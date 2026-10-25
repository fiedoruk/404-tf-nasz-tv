package pl.local.telewizjaorange.shortcut;

/** One fixed setting request. Android retains network trust and pairing checks. */
final class AdbBootPolicy {
    static final long EXPIRY_MS = 120_000L;
    static final long SCHEDULE_MS = 90_000L;
    static final long WORK_MS = 8_000L;
    enum Status { REQUEST_SENT, ALREADY_REQUESTED, EXPIRED, CANCELLED,
        PERMISSION_MISSING, DEVELOPER_DISABLED, USB_ADB_DISABLED, NO_WIFI, WRITE_REFUSED }
    interface Environment {
        long now();
        boolean cancelled();
        boolean permission();
        boolean developerEnabled();
        boolean usbAdbEnabled();
        boolean wirelessRequested();
        boolean wifiConnected();
        boolean requestWireless();
    }
    private static Status stopped(Environment env, long deadline) {
        if (env.cancelled()) return Status.CANCELLED;
        return env.now() >= deadline ? Status.EXPIRED : null;
    }
    static Status run(Environment env, long expiry) {
        long now = env.now();
        if (expiry <= now || expiry - now > EXPIRY_MS) return Status.EXPIRED;
        long deadline = Math.min(expiry, now + WORK_MS);
        Status stop = stopped(env, deadline);
        if (stop != null) return stop;
        if (!env.permission()) return Status.PERMISSION_MISSING;
        if (!env.developerEnabled()) return Status.DEVELOPER_DISABLED;
        if (!env.usbAdbEnabled()) return Status.USB_ADB_DISABLED;
        if (env.wirelessRequested()) return Status.ALREADY_REQUESTED;
        if (!env.wifiConnected()) return Status.NO_WIFI;
        stop = stopped(env, deadline);
        if (stop != null) return stop;
        return env.requestWireless() ? Status.REQUEST_SENT : Status.WRITE_REFUSED;
    }
}
