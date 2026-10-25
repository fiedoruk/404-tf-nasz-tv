package pl.local.nasztv.voiceassist.bridge;

import pl.local.nasztv.voiceassist.SessionState;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Pure HOST candidate. No Android API, HTTP, credentials, playback or thread creation. */
public final class PvrBridge {
    public static final long MAX_AGE_MS = 5000;
    public static final String CHANNELS_REQUEST = "{\"jsonrpc\":\"2.0\",\"method\":\"PVR.GetChannels\",\"params\":{\"channelgroupid\":\"alltv\",\"properties\":[\"channel\",\"channeltype\",\"hidden\",\"locked\"]},\"id\":\"nasztv-catalog\"}";
    private PvrBridge() { }

    public static final class Channel {
        public final int id;
        public final String name, type;
        public final Boolean hidden, locked;
        public Channel(int id, String name, String type, Boolean hidden, Boolean locked) {
            this.id = id; this.name = name; this.type = type; this.hidden = hidden; this.locked = locked;
        }
        private boolean valid() { return id > 0 && name != null && name.length() <= 256 &&
                ("tv".equals(type) || "radio".equals(type)) && hidden != null && locked != null; }
        private boolean eligible() { return valid() && "tv".equals(type) && !hidden && !locked; }
        private boolean same(Channel other) { return other != null && id == other.id &&
                name.equals(other.name) && type.equals(other.type) && hidden.equals(other.hidden) && locked.equals(other.locked); }
    }

    public static final class Catalog {
        public final List<Channel> channels;
        public final boolean complete;
        public final long fetchedAt;
        public Catalog(List<Channel> channels, boolean complete, long fetchedAt) {
            this.channels = channels == null ? null : Collections.unmodifiableList(new ArrayList<>(channels));
            this.complete = complete; this.fetchedAt = fetchedAt;
        }
    }

    public static final class Resolution {
        public final String status, alias;
        public final int channelId;
        public final long catalogAt;
        private Resolution(String status, String alias, int id, long catalogAt) {
            this.status = status; this.alias = alias; channelId = id; this.catalogAt = catalogAt;
        }
        public boolean matched() { return "matched".equals(status); }
    }

    private static boolean fresh(long observed, long now) {
        return observed >= 0 && now >= observed && now - observed <= MAX_AGE_MS;
    }
    private static boolean known(String alias) {
        return SessionState.knownAlias(alias);
    }
    private static String channelAlias(String name) {
        return SessionState.channelAlias(name); // Exact finite vocabulary, never substring/fuzzy.
    }
    public static Resolution resolve(String alias, Catalog catalog, long now) {
        if (!known(alias)) return new Resolution("unknown_alias", "unknown", -1, 0);
        if (catalog == null || !catalog.complete || catalog.channels == null || catalog.channels.size() > 1000)
            return new Resolution("invalid_catalog", alias, -1, 0);
        if (!fresh(catalog.fetchedAt, now)) return new Resolution("stale_catalog", alias, -1, catalog.fetchedAt);
        Map<Integer, Channel> unique = new LinkedHashMap<>();
        for (Channel channel : catalog.channels) {
            if (channel == null || !channel.valid()) return new Resolution("invalid_catalog", alias, -1, catalog.fetchedAt);
            Channel previous = unique.put(channel.id, channel);
            if (previous != null && !previous.same(channel)) return new Resolution("conflicting_id", alias, -1, catalog.fetchedAt);
        }
        int id = -1;
        for (Channel channel : unique.values()) {
            if (channel.eligible() && alias.equals(channelAlias(channel.name))) {
                if (id != -1) return new Resolution("ambiguous", alias, -1, catalog.fetchedAt);
                id = channel.id;
            }
        }
        return new Resolution(id == -1 ? "not_found" : "matched", alias, id, catalog.fetchedAt);
    }
    public static String detailsRequest(Resolution result) {
        if (result == null || !result.matched()) throw new IllegalArgumentException("No unique channel");
        return "{\"jsonrpc\":\"2.0\",\"method\":\"PVR.GetChannelDetails\",\"params\":{\"channelid\":" + result.channelId +
                ",\"properties\":[\"channel\",\"channeltype\",\"hidden\",\"locked\"]},\"id\":\"nasztv-channel\"}";
    }

    /** Implement only with a nonblocking local transport enqueue on the same session event loop. */
    public interface RequestSink { void enqueue(String request); }

    public static final class Gate {
        private enum Phase { WAITING, PENDING, CLOSED }
        private final long generation;
        private Phase phase = Phase.WAITING;
        private String alias = "unknown", status = "awaiting_final";
        private long finalAt;
        public Gate(long generation) {
            if (generation <= 0) throw new IllegalArgumentException("Invalid generation");
            this.generation = generation;
        }
        public synchronized String alias() { return alias; }
        public synchronized String status() { return status; }
        /** Only the terminal STT callback may call this, after cancel/destroy succeeded. */
        public synchronized boolean acceptFinal(long token, String outcome, String text, boolean cleanupOk, long now) {
            if (token != generation || phase != Phase.WAITING) return false;
            alias = text != null && text.matches("st:[0-9a-f]{64}") ? text : SessionState.alias(text);
            if (!"result".equals(outcome) || !cleanupOk || !known(alias) || now < 0) {
                phase = Phase.CLOSED; status = "rejected_final"; alias = "unknown"; return false;
            }
            finalAt = now; phase = Phase.PENDING; status = "awaiting_catalog"; return true;
        }
        public synchronized void cancel(long token) {
            if (token == generation && phase != Phase.CLOSED) {
                phase = Phase.CLOSED; status = "cancelled";
            }
        }
        /** Returns true only if the queue call returned. It does not mean Kodi played the channel. */
        public synchronized boolean enqueue(long token, Resolution result, Channel checkedChannel,
                long checkedAt, long now, boolean sessionShown, boolean playbackReady,
                boolean deviceQualified, RequestSink sink) {
            if (token != generation || phase != Phase.PENDING) return false;
            // A failed validation consumes this command. Never retry a stale or uncertain action.
            phase = Phase.CLOSED;
            if (!deviceQualified || !sessionShown || !playbackReady || sink == null) {
                status = "not_qualified_or_inactive"; return false;
            }
            if (!fresh(finalAt, now) || result == null || !result.matched() || !alias.equals(result.alias)
                    || !fresh(result.catalogAt, now) || result.catalogAt < finalAt
                    || !fresh(checkedAt, now) || checkedAt < result.catalogAt) {
                status = "stale_or_unresolved"; return false;
            }
            if (checkedChannel == null || !checkedChannel.eligible() || checkedChannel.id != result.channelId
                    || !alias.equals(channelAlias(checkedChannel.name))) {
                status = "channel_changed"; return false;
            }
            String request = "{\"jsonrpc\":\"2.0\",\"method\":\"Player.Open\",\"params\":{\"item\":{\"channelid\":" +
                    result.channelId + "}},\"id\":\"nasztv-voice\"}";
            status = "enqueue_attempted";
            try { sink.enqueue(request); status = "enqueued_not_confirmed"; return true; }
            catch (RuntimeException ignored) { status = "enqueue_outcome_unknown"; return false; }
        }
    }
}
