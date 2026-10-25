package pl.local.nasztv.voiceassist.bridge;
import android.util.JsonReader;
import java.io.IOException;
import java.io.Reader;

public final class AndroidJsonInput implements JsonInput {
    public static final Factory FACTORY = AndroidJsonInput::new;
    private final JsonReader reader;
    private AndroidJsonInput(Reader source) { reader = new JsonReader(source); reader.setLenient(false); }
    public String peek() throws IOException { return reader.peek().name(); }
    public void beginObject() throws IOException { reader.beginObject(); }
    public void endObject() throws IOException { reader.endObject(); }
    public void beginArray() throws IOException { reader.beginArray(); }
    public void endArray() throws IOException { reader.endArray(); }
    public String name() throws IOException { return reader.nextName(); }
    public String string() throws IOException { return reader.nextString(); }
    public boolean bool() throws IOException { return reader.nextBoolean(); }
    public void nil() throws IOException { reader.nextNull(); }
}
