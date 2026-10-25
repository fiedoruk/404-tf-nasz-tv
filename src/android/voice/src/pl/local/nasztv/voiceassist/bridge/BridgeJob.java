package pl.local.nasztv.voiceassist.bridge;
import java.io.IOException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** One finite worker; at most three queries and one Open. No retries and no background service. */
public final class BridgeJob {
    public static final long BUDGET_MS=4000;
    public interface Callback {
        void prepared(BridgeJob job,PvrBridge.Resolution resolution,PvrBridge.Channel channel,long checkedAt,boolean ready);
        void done(BridgeJob job,String status,String errorType,boolean openBytesWritten,boolean acknowledged,int calls,long elapsed);
    }
    private final CancelToken cancel=new CancelToken();
    private final CountDownLatch decision=new CountDownLatch(1);
    private final AtomicBoolean finished=new AtomicBoolean();
    private final Qualification.Source source;
    private final String fingerprint,model,alias;
    private final JsonInput.Factory json;
    private final Callback callback;
    private final LoopbackRpc rpc;
    private final long started,deadline;
    private String queued;
    private Thread worker;
    private volatile boolean qualified;
    private volatile String matchedName = "";
    private volatile long catalogMs, matchMs, detailsMs, readyMs, openMs;
    public BridgeJob(Qualification.Source source,String fingerprint,String model,String alias,
                     JsonInput.Factory json,Callback callback) {
        this(source,fingerprint,model,alias,json,callback,9090,BUDGET_MS);
    }
    BridgeJob(Qualification.Source source,String fingerprint,String model,String alias,
              JsonInput.Factory json,Callback callback,int fixturePort,long budget) {
        if(budget<=0 || budget>BUDGET_MS)throw new IllegalArgumentException("budget");
        this.source=source;this.fingerprint=fingerprint;this.model=model;this.alias=alias;
        this.json=json;this.callback=callback;started=CancelToken.now();deadline=started+budget;
        rpc=new LoopbackRpc(cancel,json,fixturePort);
    }
    public synchronized void start() {
        if(worker!=null)throw new IllegalStateException("already_started");
        worker=new Thread(this::run,"NaszTV-voice-bridge");worker.start();
    }
    public void cancel() { cancel.cancel();decision.countDown(); }
    public boolean inactive() { return finished.get() || cancel.cancelled(); }
    public boolean qualified() { return qualified; }
    public String matchedName() { return matchedName; }
    public long[] stageMillis() { return new long[]{catalogMs, matchMs, detailsMs, readyMs, openMs}; }
    /** Called under Gate on the UI loop: no file/socket/HTTP work here. */
    public synchronized void enqueue(String request) {
        if(inactive() || CancelToken.now()>=deadline || queued!=null)throw new IllegalStateException("not_pending");
        queued=request;decision.countDown();
    }
    private void done(String status,String error,boolean ack) {
        if(finished.compareAndSet(false,true)) {
            try { callback.done(this,status,error,cancel.openBytesWritten(),ack,rpc.calls(),CancelToken.now()-started); }
            catch(RuntimeException ignored) { }
        }
    }
    private void run() {
        try {
            cancel.remaining(deadline);
            qualified=Qualification.read(source.file(),fingerprint,model,json);
            if(!qualified) { done("qualification_required","",false);return; }
            cancel.remaining(deadline);
            long phase = CancelToken.now();
            PvrBridge.Catalog catalog;
            try {
                Object rawCatalog=rpc.call(PvrBridge.CHANNELS_REQUEST,"nasztv-catalog",deadline,false);
                catalog=RpcProtocol.catalog(rawCatalog,CancelToken.now());
            } finally { catalogMs = CancelToken.now() - phase; }
            phase = CancelToken.now();
            PvrBridge.Resolution resolution=PvrBridge.resolve(alias,catalog,CancelToken.now());
            matchMs = CancelToken.now() - phase;
            if(!resolution.matched()) { done(resolution.status,"",false);return; }
            for (PvrBridge.Channel entry : catalog.channels) {
                if (entry.id == resolution.channelId) { matchedName = entry.name; break; }
            }
            phase = CancelToken.now();
            PvrBridge.Channel channel;
            try { channel=RpcProtocol.details(rpc.call(PvrBridge.detailsRequest(resolution),"nasztv-channel",deadline,false)); }
            finally { detailsMs = CancelToken.now() - phase; }
            long checkedAt=CancelToken.now();
            phase = CancelToken.now();
            boolean ready;
            try { ready=RpcProtocol.ready(rpc.call(RpcProtocol.FLAGS_REQUEST,"nasztv-readiness",deadline,false)); }
            finally { readyMs = CancelToken.now() - phase; }
            cancel.remaining(deadline);
            callback.prepared(this,resolution,channel,checkedAt,ready);
            if(!decision.await(cancel.remaining(deadline),TimeUnit.MILLISECONDS))throw new IOException("decision_timeout");
            cancel.remaining(deadline);
            String request;
            synchronized(this) { request=queued; }
            if(request==null)throw new IOException("not_committed");
            qualified=Qualification.read(source.file(),fingerprint,model,json);
            if(!qualified) { done("qualification_revoked","",false);return; }
            cancel.remaining(deadline);
            phase = CancelToken.now();
            Object response;
            try { response=rpc.call(request,"nasztv-voice",deadline,true); }
            finally { openMs = CancelToken.now() - phase; }
            if(!"OK".equals(response))throw new IOException("open_ack_invalid");
            done("open_acknowledged_not_video_proof","",true);
        } catch(RpcProtocol.Refused refused) { done("rpc_refused", "Refused",false); }
        catch(Exception error) {
            done(cancel.openBytesWritten()?"open_ack_unknown":"stopped_before_open",error.getClass().getSimpleName(),false);
        } finally { finished.set(true); }
    }
}
