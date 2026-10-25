package pl.local.nasztv.voiceassist.bridge;
import java.io.IOException;
import java.io.StringReader;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Shared bounded structural parser. Rejects duplicate keys rather than overwriting them. */
public final class StrictJson {
    private final JsonInput reader;
    private int values;
    private StrictJson(JsonInput reader) { this.reader = reader; }
    public static Object parse(String text, JsonInput.Factory factory) throws IOException {
        if (text == null || text.length() > 65536) throw new IOException("json_size");
        try {
            StrictJson parser = new StrictJson(factory.open(new StringReader(text)));
            Object result = parser.value(0);
            if (!"END_DOCUMENT".equals(parser.reader.peek())) throw new IOException("json_trailing");
            return result;
        } catch (IllegalStateException | NumberFormatException error) { throw new IOException("json_invalid"); }
    }
    private String string() throws IOException {
        String value = reader.string();
        if (value.length() > 4096) throw new IOException("json_string_size");
        return value;
    }
    private Object value(int depth) throws IOException {
        if (depth > 16 || ++values > 10000) throw new IOException("json_complexity");
        String token = reader.peek();
        if ("BEGIN_OBJECT".equals(token)) {
            reader.beginObject(); Map<String,Object> object = new LinkedHashMap<>();
            while (!"END_OBJECT".equals(reader.peek())) {
                String key = reader.name();
                if (key.length() > 256 || object.size() >= 64 || object.containsKey(key)) throw new IOException("json_keys");
                object.put(key, value(depth+1));
            }
            reader.endObject(); return object;
        }
        if ("BEGIN_ARRAY".equals(token)) {
            reader.beginArray(); List<Object> array = new ArrayList<>();
            while (!"END_ARRAY".equals(reader.peek())) {
                if (array.size() >= 1000) throw new IOException("json_array_size");
                array.add(value(depth+1));
            }
            reader.endArray(); return array;
        }
        if ("STRING".equals(token)) return string();
        if ("BOOLEAN".equals(token)) return reader.bool();
        if ("NULL".equals(token)) { reader.nil(); return null; }
        if ("NUMBER".equals(token)) {
            String number = string();
            if (number.length() > 64 || !number.matches("-?(0|[1-9][0-9]*)(\\.[0-9]+)?([eE][+-]?[0-9]+)?")) throw new IOException("json_number");
            return number.matches("-?(0|[1-9][0-9]*)") ? Long.valueOf(number) : new BigDecimal(number);
        }
        throw new IOException("json_value");
    }
}
