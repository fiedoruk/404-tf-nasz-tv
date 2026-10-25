package pl.local.nasztv.voiceassist.bridge;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class RpcProtocol {
    public static final Object NOTIFICATION = new Object();
    public static final String FLAGS_REQUEST = "{\"jsonrpc\":\"2.0\",\"method\":\"XBMC.GetInfoBooleans\",\"params\":{\"booleans\":[\"Player.HasVideo\",\"Pvr.IsPlayingTv\",\"Player.Paused\",\"Player.Caching\",\"Window.IsActive(fullscreenvideo)\"]},\"id\":\"nasztv-readiness\"}";
    public static final class Refused extends IOException { public Refused() { super("rpc_refused"); } }
    private RpcProtocol() { }
    @SuppressWarnings("unchecked") public static Map<String,Object> object(Object value) throws IOException {
        if (!(value instanceof Map)) throw new IOException("object_expected"); return (Map<String,Object>)value;
    }
    public static int integer(Object value, int minimum, int maximum) throws IOException {
        if (!(value instanceof Long) || (Long)value < minimum || (Long)value > maximum) throw new IOException("integer_expected");
        return ((Long)value).intValue();
    }
    public static String text(Object value, int limit) throws IOException {
        if (!(value instanceof String) || ((String)value).length() == 0 || ((String)value).length() > limit) throw new IOException("string_expected");
        return (String)value;
    }
    public static boolean bool(Object value) throws IOException {
        if (!(value instanceof Boolean)) throw new IOException("boolean_expected"); return (Boolean)value;
    }
    public static Object response(String frame, String expectedId, JsonInput.Factory factory) throws IOException {
        Map<String,Object> reply = object(StrictJson.parse(frame,factory));
        if (!"2.0".equals(reply.get("jsonrpc"))) throw new IOException("rpc_version");
        if (!reply.containsKey("id") && reply.get("method") instanceof String && !reply.containsKey("result") && !reply.containsKey("error")) return NOTIFICATION;
        if (!expectedId.equals(reply.get("id"))) throw new IOException("rpc_id");
        if (reply.containsKey("error")) throw new Refused();
        if (!reply.containsKey("result")) throw new IOException("rpc_result");
        return reply.get("result");
    }
    public static PvrBridge.Channel channel(Object value) throws IOException {
        Map<String,Object> row = object(value);
        String type = text(row.get("channeltype"),16);
        if (!"tv".equals(type) && !"radio".equals(type)) throw new IOException("channel_type");
        return new PvrBridge.Channel(integer(row.get("channelid"),1,Integer.MAX_VALUE), text(row.get("channel"),256),
                type,bool(row.get("hidden")),bool(row.get("locked")));
    }
    public static PvrBridge.Catalog catalog(Object value, long fetchedAt) throws IOException {
        Map<String,Object> result = object(value), limits = object(result.get("limits"));
        int start=integer(limits.get("start"),0,1000), end=integer(limits.get("end"),0,1000), total=integer(limits.get("total"),0,1000);
        if (!(result.get("channels") instanceof List)) throw new IOException("channels_expected");
        List<?> rows=(List<?>)result.get("channels");
        if (start != 0 || end != total || rows.size() != total) throw new IOException("catalog_incomplete");
        List<PvrBridge.Channel> channels=new ArrayList<>(); Set<Integer> ids=new HashSet<>();
        for (Object row:rows) {
            PvrBridge.Channel channel=channel(row);
            if (!ids.add(channel.id)) throw new IOException("duplicate_channel_id");
            channels.add(channel);
        }
        return new PvrBridge.Catalog(channels,true,fetchedAt);
    }
    public static PvrBridge.Channel details(Object value) throws IOException { return channel(object(value).get("channeldetails")); }
    public static boolean ready(Object value) throws IOException {
        Map<String,Object> flags=object(value);
        boolean video=bool(flags.get("Player.HasVideo")), pvr=bool(flags.get("Pvr.IsPlayingTv"));
        boolean paused=bool(flags.get("Player.Paused")), caching=bool(flags.get("Player.Caching"));
        boolean fullscreen=bool(flags.get("Window.IsActive(fullscreenvideo)"));
        return video && pvr && !paused && !caching && fullscreen;
    }
}
