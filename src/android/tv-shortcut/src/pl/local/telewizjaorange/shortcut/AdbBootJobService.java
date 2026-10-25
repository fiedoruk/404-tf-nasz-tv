package pl.local.telewizjaorange.shortcut;

import android.Manifest;
import android.app.job.JobParameters;
import android.app.job.JobService;
import android.content.pm.PackageManager;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.provider.Settings;
import android.util.Log;
import java.util.concurrent.atomic.AtomicBoolean;

/** Finite boot maintenance; never opens Kodi, pairs clients or changes network trust. */
public final class AdbBootJobService extends JobService {
    private final Handler main = new Handler(Looper.getMainLooper());
    private Work current;

    private final class Work implements AdbBootPolicy.Environment {
        final JobParameters params;
        final long started = SystemClock.elapsedRealtime();
        final AtomicBoolean cancelled = new AtomicBoolean();
        final AtomicBoolean finished = new AtomicBoolean();
        volatile int writes;
        final Runnable timeout = () -> finish(this, "WORK_TIMEOUT");
        Work(JobParameters params) { this.params = params; }
        public long now() { return SystemClock.elapsedRealtime(); }
        public boolean cancelled() { return cancelled.get(); }
        public boolean permission() {
            return checkSelfPermission(Manifest.permission.WRITE_SECURE_SETTINGS) == PackageManager.PERMISSION_GRANTED;
        }
        public boolean developerEnabled() {
            return Settings.Global.getInt(getContentResolver(), Settings.Global.DEVELOPMENT_SETTINGS_ENABLED, 0) == 1;
        }
        public boolean usbAdbEnabled() {
            return Settings.Global.getInt(getContentResolver(), Settings.Global.ADB_ENABLED, 0) == 1;
        }
        public boolean wirelessRequested() {
            return Settings.Global.getInt(getContentResolver(), "adb_wifi_enabled", 0) == 1;
        }
        public boolean wifiConnected() {
            ConnectivityManager manager = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            Network network = manager == null ? null : manager.getActiveNetwork();
            NetworkCapabilities capabilities = network == null ? null : manager.getNetworkCapabilities(network);
            return capabilities != null && capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
                    && !capabilities.hasTransport(NetworkCapabilities.TRANSPORT_VPN);
        }
        public boolean requestWireless() {
            // Recheck cancellation immediately before the sole fixed write. An in-flight
            // framework Binder call cannot be undone by onStopJob; no later action follows.
            if (cancelled() || now() >= started + AdbBootPolicy.WORK_MS
                    || now() >= params.getExtras().getLong(AdbBootReceiver.EXPIRY, 0)) return false;
            writes++;
            return Settings.Global.putInt(getContentResolver(), "adb_wifi_enabled", 1);
        }
    }

    @Override public boolean onStartJob(JobParameters params) {
        if (Build.VERSION.SDK_INT < 30 || params.getJobId() != AdbBootReceiver.JOB_ID) return false;
        if (current != null) stop(current, "REPLACED");
        final Work work = new Work(params);
        current = work;
        main.postDelayed(work.timeout, AdbBootPolicy.WORK_MS);
        try {
            new Thread(() -> {
                String status;
                try {
                    status = AdbBootPolicy.run(work,
                            params.getExtras().getLong(AdbBootReceiver.EXPIRY, 0)).name();
                } catch (RuntimeException error) {
                    status = "PLATFORM_ERROR";
                }
                final String result = status;
                main.post(() -> finish(work, result));
            }, "NaszTV-adb-boot").start();
            return true;
        } catch (RuntimeException error) {
            stop(work, "WORKER_NOT_STARTED");
            return false;
        }
    }

    private void stop(Work work, String status) {
        work.cancelled.set(true);
        main.removeCallbacks(work.timeout);
        if (current == work) current = null;
        if (work.finished.compareAndSet(false, true)) {
            Log.i(AdbBootReceiver.TAG, "status=" + status + " writes=" + work.writes
                    + " elapsed_ms=" + (SystemClock.elapsedRealtime() - work.started));
        }
    }

    private void finish(Work work, String status) {
        if (work.finished.get()) return;
        stop(work, status);
        jobFinished(work.params, false); // Never reschedule a failed or cancelled attempt.
    }

    @Override public boolean onStopJob(JobParameters params) {
        if (current != null && current.params.getJobId() == params.getJobId()) stop(current, "SYSTEM_STOPPED");
        return false;
    }

    @Override public void onDestroy() {
        if (current != null) stop(current, "SERVICE_DESTROYED");
        super.onDestroy();
    }
}
