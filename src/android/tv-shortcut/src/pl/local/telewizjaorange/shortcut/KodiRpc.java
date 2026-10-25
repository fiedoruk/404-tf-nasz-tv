package pl.local.telewizjaorange.shortcut;

import org.json.JSONArray;
import org.json.JSONObject;
import android.system.ErrnoException;
import android.system.OsConstants;
import java.io.IOException;
import java.net.ConnectException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

/** Only the existing Kodi JSON-RPC TCP listener on this same Android device. */
public final class KodiRpc implements Recovery.Backend {
    private final LaunchGuard guard;
    private final QuitCooldown cooldown;
    private Socket current;
    private int nextId = 1;
    public KodiRpc(LaunchGuard guard, QuitCooldown cooldown) { this.guard = guard; this.cooldown = cooldown; }

    public synchronized void cancel() {
        if (current != null) try { current.close(); } catch (IOException ignored) { }
    }
    private int timeout(long deadline, int cap) throws IOException {
        if (guard.cancelled() || Thread.currentThread().isInterrupted()) throw new IOException("cancelled");
        long remaining = (deadline - System.nanoTime()) / 1_000_000L;
        if (remaining <= 0) throw new IOException("deadline");
        return (int) Math.min(remaining, cap);
    }
    private static int integer(Object value, int minimum) throws IOException {
        if (!(value instanceof Number)) throw new IOException("integer expected");
        Number n = (Number) value;
        long v = n.longValue();
        if (v < minimum || v > Integer.MAX_VALUE || n.doubleValue() != v) throw new IOException("integer range");
        return (int) v;
    }
    private Object call(String method, JSONObject params, long deadline) throws Exception {
        int id = nextId++;
        JSONObject request = new JSONObject().put("jsonrpc", "2.0").put("id", id).put("method", method);
        if (params != null) request.put("params", params);
        Socket socket = new Socket();
        synchronized (this) {
            if (guard.cancelled()) { socket.close(); throw new IOException("cancelled"); }
            current = socket;
        }
        try {
            socket.connect(new InetSocketAddress(InetAddress.getByAddress(new byte[]{127, 0, 0, 1}), 9090), timeout(deadline, 350));
            socket.setSoTimeout(timeout(deadline, 600));
            socket.getOutputStream().write((request.toString() + "\n").getBytes(StandardCharsets.UTF_8));
            RpcFrames frames = new RpcFrames(socket.getInputStream(),
                    () -> socket.setSoTimeout(timeout(deadline, 600)));
            String raw = frames.readMatching(frame -> {
                JSONObject reply = new JSONObject(frame);
                Object responseId = reply.opt("id");
                return responseId instanceof Number && ((Number) responseId).doubleValue() == id;
            });
            JSONObject reply = new JSONObject(raw);
            if (reply.has("error") || !reply.has("result")) throw new IOException("RPC unavailable");
            return reply.get("result");
        } finally {
            synchronized (this) { if (current == socket) current = null; }
            try { socket.close(); } catch (IOException ignored) { }
        }
    }
    @Override public Recovery.Active active(long deadline) throws Exception {
        JSONArray players = (JSONArray) call("Player.GetActivePlayers", null, deadline);
        int videoId = -1;
        if (players.length() == 1) {
            JSONObject player = players.getJSONObject(0);
            if ("video".equals(player.optString("type"))) videoId = integer(player.get("playerid"), 0);
        }
        return new Recovery.Active(players.length(), videoId);
    }
    @Override public Recovery.Channel channel(int playerId, long deadline) throws Exception {
        JSONObject params = new JSONObject().put("playerid", playerId)
                .put("properties", new JSONArray().put("mediapath"));
        JSONObject item = ((JSONObject) call("Player.GetItem", params, deadline)).getJSONObject("item");
        if (!"channel".equals(item.optString("type"))) return null;
        Object path = item.opt("mediapath");
        return new Recovery.Channel(integer(item.get("id"), 1), "channel", path instanceof String ? (String) path : null);
    }
    @Override public void quit(long deadline) throws Exception {
        cooldown.record(); // Persist even when the following request loses its ACK.
        Object result = call("Application.Quit", null, deadline);
        if (!"OK".equals(result)) throw new IOException("Quit unavailable");
    }
    @Override public Recovery.Port port(long deadline) throws Exception {
        Socket socket = new Socket();
        synchronized (this) {
            if (guard.cancelled()) { socket.close(); throw new IOException("cancelled"); }
            current = socket;
        }
        try {
            socket.connect(new InetSocketAddress(InetAddress.getByAddress(new byte[]{127, 0, 0, 1}), 9090), timeout(deadline, 250));
            return Recovery.Port.OPEN; // Connect only; never sends a request or payload.
        } catch (ConnectException unavailable) {
            Throwable cause = unavailable;
            for (int depth = 0; cause != null && depth < 5; depth++, cause = cause.getCause()) {
                if (cause instanceof ErrnoException && ((ErrnoException) cause).errno == OsConstants.ECONNREFUSED)
                    return Recovery.Port.REFUSED;
            }
            return Recovery.Port.UNKNOWN;
        } catch (IOException unknown) {
            return Recovery.Port.UNKNOWN; // Timeout, unreachable and cancellation are not refusal.
        } finally {
            synchronized (this) { if (current == socket) current = null; }
            try { socket.close(); } catch (IOException ignored) { }
        }
    }
}
