package pl.local.nasztv.voiceassist.bridge;
import java.io.IOException;
import java.io.Reader;

/** Native Android token reader at runtime; existing toolchain Gson only in HOST tests. */
public interface JsonInput {
    interface Factory { JsonInput open(Reader reader) throws IOException; }
    String peek() throws IOException;
    void beginObject() throws IOException;
    void endObject() throws IOException;
    void beginArray() throws IOException;
    void endArray() throws IOException;
    String name() throws IOException;
    String string() throws IOException;
    boolean bool() throws IOException;
    void nil() throws IOException;
}
