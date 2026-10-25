package pl.local.telewizjaorange.shortcut;

import java.io.ByteArrayOutputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;

/** Bounded JSON object framing, including nested objects and escaped strings. */
public final class RpcFrames {
    public interface Check { void check() throws Exception; }
    public interface Match { boolean matches(String frame) throws Exception; }
    private static final int LIMIT = 64 * 1024;
    private final InputStream input;
    private final Check check;
    private int received;
    private final byte[] chunk = new byte[1024];
    private int position, available;

    public RpcFrames(InputStream input, Check check) { this.input = input; this.check = check; }

    public String readMatching(Match match) throws Exception {
        while (true) {
            String frame = next();
            if (match.matches(frame)) return frame;
        }
    }
    private int read() throws Exception {
        while (position == available) {
            check.check(); // Update the socket timeout only before a possibly blocking read.
            int count = input.read(chunk, 0, Math.min(chunk.length, LIMIT - received + 1));
            if (count < 0) return -1;
            received += count;
            if (received > LIMIT) throw new IOException("RPC byte limit");
            position = 0;
            available = count;
        }
        return chunk[position++] & 255;
    }
    private String next() throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        int depth = 0;
        boolean quoted = false, escaped = false;
        while (true) {
            int b = read();
            if (b < 0) throw new EOFException("incomplete RPC frame");
            if (depth == 0) {
                if (b == ' ' || b == '\n' || b == '\r' || b == '\t') continue;
                if (b != '{') throw new IOException("RPC object expected");
                depth = 1;
                bytes.write(b);
                continue;
            }
            bytes.write(b);
            if (quoted) {
                if (escaped) escaped = false;
                else if (b == '\\') escaped = true;
                else if (b == '"') quoted = false;
            } else if (b == '"') quoted = true;
            else if (b == '{') depth++;
            else if (b == '}') depth--;
            if (depth == 0) {
                return StandardCharsets.UTF_8.newDecoder()
                        .onMalformedInput(CodingErrorAction.REPORT)
                        .onUnmappableCharacter(CodingErrorAction.REPORT)
                        .decode(ByteBuffer.wrap(bytes.toByteArray())).toString();
            }
        }
    }
}
