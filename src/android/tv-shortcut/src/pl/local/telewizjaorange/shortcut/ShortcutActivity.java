package pl.local.telewizjaorange.shortcut;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.SystemClock;
import android.widget.TextView;
import android.widget.Toast;

/** Visible, cancellable one-shot handoff. It never reads incoming Intent data. */
public final class ShortcutActivity extends Activity {
    private final LaunchGuard guard = new LaunchGuard();
    private KodiRpc rpc;
    private QuitCooldown cooldown;
    private boolean resumed;
    private Thread worker;
    private TextView label;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        SharedPreferences prefs = getSharedPreferences("quit_state", MODE_PRIVATE);
        cooldown = new QuitCooldown(new QuitCooldown.Store() {
            public long read() { return prefs.getLong("elapsed_ms", -1L); }
            public boolean write(long value) { return prefs.edit().putLong("elapsed_ms", value).commit(); }
            public void clear() { prefs.edit().remove("elapsed_ms").apply(); }
        }, new QuitCooldown.Clock() {
            public long elapsedMillis() { return SystemClock.elapsedRealtime(); }
            public void sleep(long milliseconds) throws InterruptedException { Thread.sleep(milliseconds); }
        });
        rpc = new KodiRpc(guard, cooldown);
        BrandingView branding = new BrandingView(this);
        label = branding.statusLabel();
        setContentView(branding);
    }
    @Override protected void onNewIntent(Intent ignored) {
        super.onNewIntent(ignored); // No new worker, no data or extras consumed.
    }
    @Override protected void onResume() {
        super.onResume();
        resumed = true;
        beginIfReady();
    }
    @Override public void onWindowFocusChanged(boolean focused) {
        super.onWindowFocusChanged(focused);
        if (focused) beginIfReady();
        else if (guard.started() && !guard.handedOff()) cancelWork();
    }
    private void beginIfReady() {
        if (!resumed || !hasWindowFocus() || !guard.startOnce()) return;
        worker = new Thread(() -> {
            Recovery.Clock clock = new Recovery.Clock() {
                public long now() { return System.nanoTime(); }
                public void sleep(long milliseconds) throws InterruptedException { Thread.sleep(milliseconds); }
            };
            Recovery.Progress progress = seconds -> runOnUiThread(() -> {
                if (resumed && hasWindowFocus() && !guard.cancelled() && !guard.handedOff())
                    label.setText(seconds > 0 ? "Przygotowanie: " + seconds + " s" : "Kończę przygotowanie…");
            });
            Recovery.Plan result;
            try {
                result = cooldown.await(guard, progress)
                        ? new Recovery(rpc, clock, guard, progress).run(System.nanoTime() + 4_000_000_000L)
                        : Recovery.Plan.cancel();
            } catch (Exception unavailable) { result = Recovery.Plan.cancel(); }
            final Recovery.Plan plan = result;
            runOnUiThread(() -> handoff(plan));
        }, "tv-one-shot");
        worker.start();
    }
    private void handoff(Recovery.Plan plan) {
        if (plan.action == Recovery.Action.CANCEL || guard.cancelled() || !resumed || !hasWindowFocus()) {
            finish();
            return;
        }
        try {
            Intent launch = getPackageManager().getLeanbackLaunchIntentForPackage("org.xbmc.kodi");
            if (!guard.claimHandoff(resumed, hasWindowFocus())) return;
            if (launch == null) {
                Toast.makeText(this, "Kodi nie jest zainstalowane.", Toast.LENGTH_SHORT).show();
            } else {
                startActivity(launch);
            }
        } catch (ActivityNotFoundException | SecurityException unavailable) {
            if (resumed && hasWindowFocus() && !guard.cancelled())
                Toast.makeText(this, "Nie można teraz otworzyć Kodi.", Toast.LENGTH_SHORT).show();
        } finally {
            finish();
        }
    }
    private void cancelWork() {
        guard.cancel();
        if (rpc != null) rpc.cancel();
        if (worker != null) worker.interrupt();
    }
    @Override protected void onPause() {
        resumed = false;
        if (!guard.handedOff()) cancelWork();
        super.onPause();
        if (!guard.handedOff()) finish();
    }
    @Override protected void onDestroy() {
        if (!guard.handedOff()) cancelWork();
        super.onDestroy();
    }
}
