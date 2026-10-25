package pl.local.telewizjaorange.shortcut;

import android.app.job.JobInfo;
import android.app.job.JobScheduler;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.PersistableBundle;
import android.os.SystemClock;
import android.util.Log;

/** BOOT only enqueues one non-persistent job. Manual action is sender-DUMP protected. */
public final class AdbBootReceiver extends BroadcastReceiver {
    static final int JOB_ID = 7351;
    static final String TAG = "NaszTVAdb";
    static final String TEST_ACTION = "pl.local.telewizjaorange.shortcut.TEST_ADB_BOOT";
    static final String EXPIRY = "expiry_elapsed_ms";

    @Override public void onReceive(Context context, Intent intent) {
        String action = intent == null ? null : intent.getAction();
        if (!Intent.ACTION_BOOT_COMPLETED.equals(action) && !TEST_ACTION.equals(action)) return;
        if (Build.VERSION.SDK_INT < 30) {
            Log.i(TAG, "status=UNSUPPORTED_ANDROID");
            return;
        }
        // No extras, settings names, values, network identities or commands from the sender.
        PersistableBundle extras = new PersistableBundle();
        extras.putLong(EXPIRY, SystemClock.elapsedRealtime() + AdbBootPolicy.EXPIRY_MS);
        JobInfo job = new JobInfo.Builder(JOB_ID,
                new ComponentName(context, AdbBootJobService.class))
                .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
                .setOverrideDeadline(AdbBootPolicy.SCHEDULE_MS)
                .setPersisted(false).setExtras(extras).build();
        try {
            JobScheduler scheduler = (JobScheduler) context.getSystemService(Context.JOB_SCHEDULER_SERVICE);
            int result = scheduler == null ? JobScheduler.RESULT_FAILURE : scheduler.schedule(job);
            Log.i(TAG, result == JobScheduler.RESULT_SUCCESS ? "status=ENQUEUED" : "status=ENQUEUE_FAILED");
        } catch (RuntimeException error) {
            Log.i(TAG, "status=ENQUEUE_FAILED");
        }
    }
}
