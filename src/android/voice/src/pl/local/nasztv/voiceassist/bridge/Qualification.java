package pl.local.nasztv.voiceassist.bridge;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Map;

/** Private, version/build/model-specific opt-in. Never writes a qualification file. */
public final class Qualification {
    public interface Source { File file(); }
    private Qualification() { }
    private static boolean concrete(String value) {
        return value!=null && !value.trim().isEmpty() && !"unknown".equalsIgnoreCase(value.trim());
    }
    public static boolean read(File file, String fingerprint, String model, JsonInput.Factory factory) throws IOException {
        if (!file.isFile()) return false;
        byte[] buffer=new byte[1025];int used=0;
        try (FileInputStream input=new FileInputStream(file)) {
            while (used<buffer.length) { int n=input.read(buffer,used,buffer.length-used);if(n<0)break;used+=n; }
        }
        if (used==0 || used>1024) return false;
        String text=StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(buffer,0,used)).toString();
        Map<String,Object> value=RpcProtocol.object(StrictJson.parse(text,factory));
        return value.keySet().equals(new HashSet<>(Arrays.asList("schema","version","fingerprint","model","surface_and_mic_qualified")))
                && Long.valueOf(1).equals(value.get("schema")) && "0.1.4".equals(value.get("version"))
                && concrete(fingerprint) && fingerprint.equals(value.get("fingerprint"))
                && concrete(model) && model.equals(value.get("model"))
                && Boolean.TRUE.equals(value.get("surface_and_mic_qualified"));
    }
}
