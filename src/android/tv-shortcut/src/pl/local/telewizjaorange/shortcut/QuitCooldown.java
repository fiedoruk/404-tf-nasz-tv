package pl.local.telewizjaorange.shortcut;

import java.io.IOException;

/** The only persistent value: monotonic elapsed milliseconds before the last Quit attempt. */
public final class QuitCooldown {
    public interface Store {
        long read();
        boolean write(long elapsedMillis);
        void clear();
    }
    public interface Clock {
        long elapsedMillis();
        void sleep(long milliseconds) throws InterruptedException;
    }
    private final Store store;
    private final Clock clock;
    public QuitCooldown(Store store, Clock clock) { this.store = store; this.clock = clock; }

    /** Commit before sending Quit; failed persistence must prevent that request. */
    public void record() throws IOException {
        if (!store.write(clock.elapsedMillis())) throw new IOException("Quit state unavailable");
    }
    public boolean await(LaunchGuard guard, Recovery.Progress progress) throws InterruptedException {
        long stamp = store.read();
        int shown = -1;
        while (!guard.cancelled() && !Thread.currentThread().isInterrupted()) {
            if (stamp < 0) { store.clear(); return true; }
            long now = clock.elapsedMillis();
            if (now < stamp || now - stamp >= 15_000L) {
                store.clear(); // Expired, or elapsed clock reset after reboot.
                return true;
            }
            long remaining = 15_000L - (now - stamp);
            int seconds = (int) ((remaining + 999L) / 1000L);
            if (shown != seconds) { progress.waiting(seconds); shown = seconds; }
            clock.sleep(Math.min(250L, remaining));
        }
        return false; // Home never clears a live cooldown for the next Activity/process.
    }
}
