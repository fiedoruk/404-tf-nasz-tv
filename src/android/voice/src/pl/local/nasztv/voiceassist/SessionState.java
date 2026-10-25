package pl.local.nasztv.voiceassist;

import java.text.Normalizer;
import java.util.Locale;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.regex.Pattern;
import java.util.LinkedHashMap;
import java.util.Map;

/** Main-thread one-shot lifecycle; raw recognition text is never retained. */
public final class SessionState {
    private static final Map<String, Pattern> PATTERNS = new LinkedHashMap<>();
    private static final Map<String, String> KEYS = new LinkedHashMap<String, String>(512, .75f, true) {
        @Override protected boolean removeEldestEntry(Map.Entry<String, String> entry) { return size() > 512; }
    };
    private static Pattern pattern(String expression) {
        synchronized (PATTERNS) {
            Pattern p = PATTERNS.get(expression);
            if (p == null) { p = Pattern.compile(expression); PATTERNS.put(expression, p); }
            return p;
        }
    }
    private static String replace(String value, String expression, String replacement) {
        return pattern(expression).matcher(value).replaceAll(replacement);
    }
    public static final long LIMIT_MS = 30000; // Diagnostic cap, not a product latency promise.
    public interface Effects {
        boolean cleanup();
        void record(String outcome, int error, String alias, int chars, long elapsed);
    }
    private boolean started, done;
    private long startedAt;
    public boolean begin(long now) {
        if (started || done) return false;
        started = true; startedAt = now; return true;
    }
    public boolean started() { return started; }
    public boolean done() { return done; }
    public boolean expired(long now) { return started && now - startedAt >= LIMIT_MS; }
    public boolean complete(String outcome, int error, String text, long now, Effects effects) {
        if (done) return false;
        done = true; // Reentrant/late callbacks cannot write a second receipt.
        long elapsed = started ? Math.max(0, now - startedAt) : 0;
        boolean clean = effects.cleanup();
        boolean result = clean && "result".equals(outcome);
        effects.record(clean ? outcome : "cleanup_error", clean ? error : -2,
                result ? alias(text) : "unknown", result && text != null ? text.codePointCount(0, text.length()) : 0, elapsed);
        return true;
    }
    public static String alias(String text) {
        if (text == null || text.length() > 256) return "unknown";
        String value = replace(normalize(text), "[.,!?]", "").trim();
        value = pattern("^(przelacz na |wlacz |kanal (?!plus\\b))").matcher(value).replaceFirst("");
        return uncachedChannelAlias(value); // Spoken text never enters the public-name cache.
    }
    private static String normalize(String value) {
        String nfd = Normalizer.normalize(value.toLowerCase(Locale.ROOT).replace('ł', 'l'), Normalizer.Form.NFD);
        return replace(replace(nfd, "\\p{M}+", "").trim(), "\\s+", " ");
    }
    /** Catalogue keys are transient matching tokens, never stored as speech receipts. */
    public static String channelAlias(String text) {
        if (text == null || text.length() > 256) return "unknown";
        synchronized (KEYS) { String key = KEYS.get(text); if (key != null) return key; }
        String key = uncachedChannelAlias(text);
        synchronized (KEYS) { KEYS.put(text, key); }
        return key;
    }
    private static String uncachedChannelAlias(String text) {
        if(text==null || text.length()>256)return "unknown";
        String value=pattern(" (hd|sd|uhd|4k)$").matcher(normalize(text)).replaceFirst("");
        if (value.equals("tvn") || value.equals("te fau en") || value.equals("te fal en")) return "TVN";
        if (value.equals("polsat")) return "Polsat";
        if (value.equals("tvn24") || value.equals("tvn 24") || value.equals("tvn dwadziescia cztery")) return "TVN24";
        if(value.equals("tvp1") || value.equals("tvp 1") || value.equals("tvp jeden") || value.equals("te fau pe jeden"))return "TVP1";
        if(value.equals("tvp2") || value.equals("tvp 2") || value.equals("tvp dwa") || value.equals("te fau pe dwa"))return "TVP2";
        if(value.equals("tvpinfo") || value.equals("tvp info") || value.equals("te fau pe info"))return "TVPInfo";
        if(value.equals("polsatnews") || value.equals("polsat news") || value.equals("polsat nius"))return "PolsatNews";
        if(value.equals("wydarzenia24") || value.equals("wydarzenia 24") || value.equals("wydarzenia dwadziescia cztery"))return "Wydarzenia24";
        value = replace(value, "\\bte (fau|fal) en\\b", "tvn");
        value = replace(value, "\\bte (fau|fal) pe\\b", "tvp");
        value = replace(value, "\\b(stajl|styl)\\b", "style");
        value = replace(value, "\\b(nius|niuz)\\b", "news");
        value = replace(value, "\\bkanal (zero|0)\\b", "zero");
        value = replace(value, "\\bplus\\b", "+");
        value = replace(value, "\\bkanal\\s*\\+", "canal+");
        value = replace(value, "\\bdwadziescia cztery\\b", "24");
        value = replace(value, "\\b(trzynascie|trzynasta)\\b", "13");
        String[] digits = {"jeden", "dwa", "trzy", "cztery", "piec", "szesc", "siedem", "osiem", "dziewiec"};
        for (int i = 0; i < digits.length; i++) value = replace(value, "\\b" + digits[i] + "\\b", Integer.toString(i + 1));
        value = replace(value.replace('&', 'i'), "[\\s.!,?_'’–—-]+", "");
        if (value.equals("0")) value = "zero";
        if (value.isEmpty() || !pattern("[a-z0-9+]+").matcher(value).matches()) return "unknown";
        // Preserve existing public aliases even when normalized from a new pronunciation.
        if (value.equals("tvn")) return "TVN";
        if (value.equals("tvn24")) return "TVN24";
        if (value.equals("tvp1")) return "TVP1";
        if (value.equals("tvp2")) return "TVP2";
        if (value.equals("tvpinfo")) return "TVPInfo";
        if (value.equals("polsatnews")) return "PolsatNews";
        if (value.equals("wydarzenia24")) return "Wydarzenia24";
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder key = new StringBuilder("st:");
            final String hex = "0123456789abcdef";
            for (byte b : digest) { key.append(hex.charAt((b & 255) >>> 4)); key.append(hex.charAt(b & 15)); }
            return key.toString();
        } catch (java.security.NoSuchAlgorithmException impossible) { return "unknown"; }
    }
    public static boolean knownAlias(String alias) {
        return (alias != null && pattern("st:[0-9a-f]{64}").matcher(alias).matches()) || "TVP1".equals(alias) || "TVP2".equals(alias) || "TVN".equals(alias) || "Polsat".equals(alias)
                || "TVN24".equals(alias) || "TVPInfo".equals(alias) || "PolsatNews".equals(alias) || "Wydarzenia24".equals(alias);
    }
}
