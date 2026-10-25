package pl.local.telewizjaorange.shortcut;

import java.util.concurrent.atomic.AtomicBoolean;

/** One Activity instance owns at most one worker and one foreground handoff. */
public final class LaunchGuard {
    private final AtomicBoolean started = new AtomicBoolean();
    private final AtomicBoolean cancelled = new AtomicBoolean();
    private final AtomicBoolean handedOff = new AtomicBoolean();

    public boolean startOnce() { return !cancelled.get() && started.compareAndSet(false, true); }
    public void cancel() { cancelled.set(true); }
    public boolean cancelled() { return cancelled.get(); }
    public boolean handedOff() { return handedOff.get(); }
    public boolean started() { return started.get(); }

    /** Called only on the Android UI thread, immediately before startActivity. */
    public boolean claimHandoff(boolean resumed, boolean focused) {
        return resumed && focused && started.get() && !cancelled.get()
                && handedOff.compareAndSet(false, true);
    }
}
