package pl.local.telewizjaorange.shortcut;

import java.io.IOException;
import java.net.URI;

/** Pure decision core. Returns one handoff plan; never launches an Activity. */
public final class Recovery {
    public interface Clock {
        long now();
        void sleep(long milliseconds) throws InterruptedException;
    }
    public interface Backend {
        Active active(long deadline) throws Exception;
        Channel channel(int playerId, long deadline) throws Exception;
        void quit(long deadline) throws Exception;
        Port port(long deadline) throws Exception;
    }
    public interface Progress { void waiting(int seconds); }
    public enum Port { OPEN, REFUSED, UNKNOWN }
    public static final class Active {
        public final int count, videoPlayerId;
        public Active(int count, int videoPlayerId) {
            this.count = count;
            this.videoPlayerId = videoPlayerId;
        }
        public boolean oneVideo() { return count == 1 && videoPlayerId >= 0; }
    }
    public static final class Channel {
        public final int id;
        public final String type, mediaPath;
        public Channel(int id, String type, String mediaPath) {
            this.id = id; this.type = type; this.mediaPath = mediaPath;
        }
        public boolean valid() {
            if (id <= 0 || !"channel".equals(type) || mediaPath == null
                    || !mediaPath.startsWith("pvr://channels/tv/") || !mediaPath.endsWith(".pvr")) return false;
            try {
                URI uri = new URI(mediaPath);
                return "pvr".equals(uri.getScheme()) && "channels".equals(uri.getHost())
                        && uri.getUserInfo() == null && uri.getPort() == -1
                        && uri.getQuery() == null && uri.getFragment() == null;
            } catch (Exception invalid) { return false; }
        }
        public boolean same(Channel other) {
            return other != null && other.valid() && id == other.id && mediaPath.equals(other.mediaPath);
        }
    }
    public enum Action { LEANBACK, CANCEL }
    public static final class Plan {
        public final Action action;
        private Plan(Action action) { this.action = action; }
        public static Plan fallback() { return new Plan(Action.LEANBACK); }
        public static Plan cancel() { return new Plan(Action.CANCEL); }
    }

    private final Backend backend;
    private final Clock clock;
    private final LaunchGuard guard;
    private final Progress progress;

    public Recovery(Backend backend, Clock clock, LaunchGuard guard, Progress progress) {
        this.backend = backend; this.clock = clock; this.guard = guard; this.progress = progress;
    }
    private void check(long deadline) throws IOException, InterruptedException {
        if (guard.cancelled() || Thread.currentThread().isInterrupted()) throw new InterruptedException();
        if (clock.now() >= deadline) throw new IOException("deadline");
    }
    public Plan run(long preparationDeadline) {
        boolean quitAttempted = false;
        boolean emptyObserved = false;
        try {
            check(preparationDeadline);
            Active initial = backend.active(preparationDeadline);
            if (initial.count == 0) {
                emptyObserved = true;
                check(preparationDeadline);
                Active fresh = backend.active(preparationDeadline);
                if (fresh == null || fresh.count != 0) return Plan.cancel();
            } else {
                if (!initial.oneVideo()) return Plan.fallback();
                check(preparationDeadline);
                Channel first = backend.channel(initial.videoPlayerId, preparationDeadline);
                if (first == null || !first.valid()) return Plan.fallback();
                check(preparationDeadline);
                Channel fresh = backend.channel(initial.videoPlayerId, preparationDeadline);
                if (!first.same(fresh)) return Plan.cancel();
            }
            check(preparationDeadline);
            quitAttempted = true; // Lost ACK is consumed: no retry and no fallback launch.
            long sentAt = clock.now();
            long deadline = sentAt + 15_000_000_000L;
            backend.quit(Math.min(preparationDeadline, deadline)); // ACK required.
            long refusedSince = -1;
            int shownSeconds = -1;
            while (true) {
                check(deadline);
                Port state = backend.port(deadline);
                check(deadline);
                long now = clock.now();
                if (state == Port.UNKNOWN) return Plan.cancel();
                if (state == Port.OPEN && refusedSince >= 0) return Plan.cancel();
                if (state == Port.REFUSED && refusedSince < 0) refusedSince = now;
                if (now - sentAt >= 10_000_000_000L && refusedSince >= 0
                        && now - refusedSince >= 2_000_000_000L) return Plan.fallback();
                int seconds = (int) Math.max(0, (sentAt + 10_000_000_000L - now + 999_999_999L) / 1_000_000_000L);
                if (shownSeconds != seconds) { progress.waiting(seconds); shownSeconds = seconds; }
                long remainingMs = (deadline - clock.now()) / 1_000_000L;
                if (remainingMs <= 0) return Plan.cancel();
                clock.sleep(Math.min(250, remainingMs));
            }
        } catch (Exception unavailable) {
            return guard.cancelled() || quitAttempted || emptyObserved || unavailable instanceof InterruptedException
                    ? Plan.cancel() : Plan.fallback();
        }
    }
}
