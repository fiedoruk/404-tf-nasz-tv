package pl.local.nasztv.voiceassist;

import android.Manifest;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.service.voice.VoiceInteractionSession;
import android.speech.RecognitionListener;
import android.speech.RecognitionSupport;
import android.speech.RecognitionSupportCallback;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;
import pl.local.nasztv.voiceassist.bridge.AndroidJsonInput;
import pl.local.nasztv.voiceassist.bridge.BridgeJob;
import pl.local.nasztv.voiceassist.bridge.CancelToken;
import pl.local.nasztv.voiceassist.bridge.PvrBridge;

/** A voice session window, not an Activity. One explicit OK starts one STT session. */
public final class AssistSession extends VoiceInteractionSession {
    private static final AtomicLong GENERATIONS=new AtomicLong();
    private static final long AUTO_HIDE_MS=1500;
    private static final ComponentName PROVIDER = new ComponentName("com.google.android.tts",
            "com.google.android.apps.speech.tts.googletts.service.GoogleTTSRecognitionService");
    private final Handler main = new Handler(Looper.getMainLooper());
    private SessionState state = new SessionState();
    private SpeechRecognizer recognizer;
    private TextView status;
    private Button listen;
    private long generation;
    private int rmsCount;
    private BridgeJob bridge;
    private PvrBridge.Gate bridgeGate;
    private InvocationPolicy invocation;
    private Runnable autoHide;
    private int startCalls,cancelCalls,destroyCalls;
    private boolean shown, ready, beginning, ended, cleanupConfirmed;
    private String support = "not_checked";
    private int supportError = -1;
    private boolean plInstalled, plSupported, plPending, plOnline;
    private final Runnable deadline = () -> complete("timeout", -1, null);
    private final Runnable supportDeadline = () -> {
        support = "query_timeout";
        complete("support_query_timeout", -1, null);
    };

    public AssistSession(Context context) { super(context); }

    @Override public View onCreateContentView() {
        LinearLayout view = new LinearLayout(getContext());
        view.setOrientation(LinearLayout.VERTICAL);
        view.setPadding(32, 12, 32, 12);
        view.setGravity(Gravity.CENTER);
        view.setBackgroundColor(Color.rgb(245, 243, 236));
        status = new TextView(getContext()); status.setTextSize(22);
        status.setTextColor(Color.rgb(25, 59, 67)); status.setGravity(Gravity.CENTER);
        status.setText("Nasz TV — próba głosu. Sprawdzam usługę bez mikrofonu…");
        view.addView(status);
        listen = new Button(getContext()); listen.setText("Słuchaj · OK"); listen.setTextSize(20);
        listen.setEnabled(false); listen.setOnClickListener(v -> begin());
        view.addView(listen);
        return view;
    }

    @Override public void onShow(Bundle args, int flags) {
        super.onShow(args, flags);
        if (shown) return;
        cancelInvocation();
        cancelBridge();
        bridge=null;bridgeGate=null;
        shown = true; generation=GENERATIONS.incrementAndGet(); state = new SessionState();
        invocation=new InvocationPolicy(generation,flags);
        startCalls=cancelCalls=destroyCalls=0;
        cleanupConfirmed=false;
        ready = beginning = ended = false; rmsCount = 0;
        plInstalled = plSupported = plPending = plOnline = false;
        support = "checking"; supportError = -1;
        if (listen != null) { listen.setEnabled(false);listen.setVisibility(invocation.automaticEligible()?View.GONE:View.VISIBLE); }
        setStatus(invocation.automaticEligible()?"Przytrzymaj przycisk. Przygotowuję nasłuch…":"Tryb diagnostyczny. Sprawdzam język bez mikrofonu…");
        preflight(generation);
    }

    private Intent request() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pl-PL");
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        return intent;
    }

    private void preflight(final long token) {
        try {
            ServiceInfo service = getContext().getPackageManager().getServiceInfo(PROVIDER, 0);
            if (!service.enabled || !service.applicationInfo.enabled || !service.exported) {
                complete("provider_unavailable", -1, null); return;
            }
            recognizer = SpeechRecognizer.createSpeechRecognizer(getContext(), PROVIDER);
            recognizer.setRecognitionListener(new Listener(token));
            main.postDelayed(supportDeadline, 5000);
            recognizer.checkRecognitionSupport(request(), getContext().getMainExecutor(), new RecognitionSupportCallback() {
                @Override public void onSupportResult(RecognitionSupport info) {
                    if (!active(token)) return;
                    support = "supported";
                    plInstalled = hasPolish(info.getInstalledOnDeviceLanguages());
                    plSupported = hasPolish(info.getSupportedOnDeviceLanguages());
                    plPending = hasPolish(info.getPendingOnDeviceLanguages());
                    plOnline = hasPolish(info.getOnlineLanguages());
                    allowStart(token);
                }
                @Override public void onError(int error) {
                    if (!active(token)) return;
                    supportError = error;
                    support = "query_error";
                    if (error == SpeechRecognizer.ERROR_CANNOT_CHECK_SUPPORT) allowStart(token);
                    else complete("support_error", error, null);
                }
            });
        } catch (PackageManager.NameNotFoundException e) { complete("provider_missing", -1, null); }
        catch (RuntimeException e) { complete("preflight_error", -1, null); }
    }

    private static boolean hasPolish(List<String> languages) {
        for (String language : languages) if (language.equalsIgnoreCase("pl") || language.equalsIgnoreCase("pl-PL")) return true;
        return false;
    }
    private boolean active(long token) { return token == generation && shown && !state.done(); }
    private void setStatus(String text) { if (status != null) status.setText(text); }
    private void allowStart(long token) {
        if(!active(token))return;
        main.removeCallbacks(supportDeadline);
        write("capability.json", "capability_only", supportError, "unknown", 0, 0, false);
        if(invocation.claimStart(token,shown,state.started(),state.done())) {
            if(listen!=null)listen.setEnabled(true);
            begin();return;
        }
        if(invocation.automaticEligible())return; // A repeated capability callback cannot restart STT.
        setStatus("Tryb diagnostyczny — źródło nie kwalifikuje auto-startu.\nOK: jedna próba. Wstecz: zamknij.");
        if (listen != null) { listen.setEnabled(true);listen.setVisibility(View.VISIBLE);listen.requestFocus(); }
    }

    private void begin() {
        if (!shown || recognizer == null || state.started() || state.done() || listen == null || !listen.isEnabled()) return;
        if (getContext().checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            complete("permission_denied", SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS, null); return;
        }
        if (!state.begin(SystemClock.elapsedRealtime())) return;
        listen.setEnabled(false); main.postDelayed(deadline, SessionState.LIMIT_MS);
        setStatus("Przygotowuję mikrofon…\nWstecz: anuluj.");
        try { startCalls++;recognizer.startListening(request()); }
        catch (RuntimeException e) { complete("start_error", -1, null); }
    }

    private boolean cleanup() {
        main.removeCallbacks(deadline); main.removeCallbacks(supportDeadline);
        SpeechRecognizer old = recognizer; recognizer = null;
        boolean ok = true;
        if (old != null) {
            try { cancelCalls++;old.cancel(); } catch (RuntimeException e) { ok = false; }
            try { destroyCalls++;old.destroy(); } catch (RuntimeException e) { ok = false; }
        }
        return ok;
    }
    private void complete(String outcome, int error, String text) {
        state.complete(outcome, error, text, SystemClock.elapsedRealtime(), new SessionState.Effects() {
            @Override public boolean cleanup() { return AssistSession.this.cleanup(); }
            @Override public void record(String result, int code, String alias, int chars, long elapsed) {
                boolean clean = !result.equals("cleanup_error");
                cleanupConfirmed=clean;
                write("receipt.json", result, code, alias.startsWith("st:") ? "catalogue_candidate" : alias, chars, elapsed, clean);
                if (listen != null) listen.setEnabled(false);
                setStatus(!clean ? "Nie potwierdzono końca nasłuchu." :
                        result.equals("result") && !alias.equals("unknown") ? "Sprawdzam nazwę kanału…" :
                        "Nie rozpoznano kanału.");
                if(clean && result.equals("result") && !alias.equals("unknown") && shown) startBridge(alias);
                else scheduleAutoHide(generation);
            }
        });
    }
    private boolean write(String name, String outcome, int error, String alias, int chars, long elapsed, boolean cleanupCalls) {
        try {
            JSONObject object = new JSONObject().put("schema", 1).put("version", "0.1.4").put("status", outcome).put("error", error)
                    .put("time_utc_ms", System.currentTimeMillis()).put("elapsed_ms", elapsed)
                    .put("alias", alias).put("char_count", chars).put("generation", generation)
                    .put("support", support).put("support_error", supportError)
                    .put("pl_installed", plInstalled).put("pl_supported", plSupported)
                    .put("pl_pending", plPending).put("pl_online", plOnline)
                    .put("ready", ready).put("beginning", beginning).put("end_of_speech", ended)
                    .put("rms_callback_count", rmsCount).put("cleanup_calls_completed", cleanupCalls)
                    .put("physical_microphone_closed_verified", false);
            addInvocationMetadata(object);
            PrivateFiles.write(getContext(),generation,name,object);return true; // Queued, not a disk-success claim.
        } catch (Exception e) { return false; }
    }

    private void startBridge(String alias) {
        final long token=generation;
        final PvrBridge.Gate gate=new PvrBridge.Gate(token);
        if(!gate.acceptFinal(token,"result",alias,true,CancelToken.now()))return;
        bridgeGate=gate;
        bridge=new BridgeJob(PrivateFiles.qualification(getContext()),Build.FINGERPRINT,Build.MODEL,alias,
                AndroidJsonInput.FACTORY,new BridgeJob.Callback() {
            @Override public void prepared(BridgeJob job,PvrBridge.Resolution resolution,PvrBridge.Channel channel,long checkedAt,boolean ready) {
                main.post(()->{
                    if(generation!=token || !shown || bridge!=job || job.inactive()) { gate.cancel(token);job.cancel();return; }
                    // Qualification was checked from the exact private file by this same finite worker.
                    if(!gate.enqueue(token,resolution,channel,checkedAt,CancelToken.now(),shown,ready,job.qualified(),job::enqueue))job.cancel();
                });
            }
            @Override public void done(BridgeJob job,String result,String error,boolean wrote,boolean ack,int calls,long elapsed) {
                main.post(()->{
                    if(generation!=token || bridge!=job)return;
                    try {
                        long[] stages = job.stageMillis();
                        JSONObject receipt=new JSONObject().put("schema",1).put("version","0.1.4")
                            .put("generation",token).put("time_utc_ms",System.currentTimeMillis())
                            .put("status",result).put("error_type",error).put("alias",job.matchedName().isEmpty() ? "unknown" : job.matchedName())
                            .put("elapsed_ms",elapsed).put("rpc_calls",calls).put("open_bytes_written",wrote)
                            .put("catalog_ms",stages[0]).put("match_ms",stages[1]).put("details_ms",stages[2])
                            .put("ready_ms",stages[3]).put("open_ms",stages[4])
                            .put("open_acknowledged",ack).put("channel_changed_verified",false).put("physical_video_verified",false);
                        addInvocationMetadata(receipt);
                        PrivateFiles.write(getContext(),token,"bridge-receipt.json",receipt);
                    } catch(Exception ignored) { }
                    if(shown) setStatus(result.equals("qualification_required") ?
                        "Próba bez zmiany kanału." :
                        ack ? "Włączam: "+job.matchedName() :
                        wrote ? "Nie można potwierdzić wykonania polecenia." :
                        result.equals("not_found") ? "Nie znalazłem takiego kanału. Spróbuj pełnej nazwy." :
                        result.equals("ambiguous") ? "Nazwa pasuje do kilku kanałów. Wybierz z listy przyciskiem OK." :
                        "Nie wysłano zmiany kanału.");
                    scheduleAutoHide(token);
                });
            }
        });
        setStatus("Sprawdzam kanał…\nWstecz: anuluj.");
        bridge.start();
    }
    private void cancelBridge() {
        if(bridgeGate!=null)bridgeGate.cancel(generation);
        if(bridge!=null)bridge.cancel();
    }
    private void addInvocationMetadata(JSONObject object) throws Exception {
        object.put("show_flags",invocation==null?0:invocation.flags())
            .put("show_source",invocation==null?"unspecified":invocation.source())
            .put("automatic_start_eligible",invocation!=null && invocation.automaticEligible())
            .put("automatic_start_taken",invocation!=null && invocation.claimed())
            .put("start_listening_calls",startCalls).put("cancel_calls",cancelCalls).put("destroy_calls",destroyCalls);
    }
    private void scheduleAutoHide(long token) {
        final InvocationPolicy ticket=invocation;
        if(ticket==null || token!=generation || !ticket.mayHide(generation,shown,state.done(),bridge!=null&&!bridge.inactive(),cleanupConfirmed))return;
        if(autoHide!=null)main.removeCallbacks(autoHide);
        autoHide=()->{
            if(token==generation && ticket.mayHide(generation,shown,state.done(),bridge!=null&&!bridge.inactive(),cleanupConfirmed))hide();
        };
        main.postDelayed(autoHide,AUTO_HIDE_MS);
    }
    private void cancelInvocation() {
        if(invocation!=null)invocation.cancel();
        if(autoHide!=null)main.removeCallbacks(autoHide);
        autoHide=null;
    }
    @Override public void onBackPressed() { cancelInvocation();cancelBridge();complete("cancelled_back", -1, null); hide(); }
    @Override public void onCloseSystemDialogs() { cancelInvocation();cancelBridge();complete("cancelled_home", -1, null); hide(); }
    @Override public void onHide() { shown=false;cancelInvocation();cancelBridge();complete("cancelled_hide", -1, null);super.onHide(); }
    @Override public void onDestroy() { shown=false;cancelInvocation();cancelBridge();complete("cancelled_destroy", -1, null);cleanup();super.onDestroy(); }

    private final class Listener implements RecognitionListener {
        private final long token;
        Listener(long token) { this.token = token; }
        @Override public void onReadyForSpeech(Bundle ignored) { if (active(token)) { ready = true; setStatus("Słucham…"); } }
        @Override public void onBeginningOfSpeech() { if (active(token)) beginning = true; }
        @Override public void onRmsChanged(float ignored) { if (active(token)) rmsCount++; }
        @Override public void onEndOfSpeech() { if (active(token)) ended = true; }
        @Override public void onError(int error) { if (active(token)) complete("recognition_error", error, null); }
        @Override public void onResults(Bundle results) {
            if (!active(token)) return;
            if (state.expired(SystemClock.elapsedRealtime())) { complete("timeout", -1, null); return; }
            ArrayList<String> values = results == null ? null : results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            complete(values == null || values.isEmpty() ? "no_result" : "result", 0,
                    values == null || values.isEmpty() ? null : values.get(0));
        }
        @Override public void onBufferReceived(byte[] ignored) { }
        @Override public void onPartialResults(Bundle ignored) { }
        @Override public void onEvent(int type, Bundle ignored) { }
    }
}
