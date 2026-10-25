package pl.local.nasztv.voiceassist;

import android.content.Context;
import android.util.AtomicFile;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import pl.local.nasztv.voiceassist.bridge.Qualification;

/** Small technical receipts only. All filesystem calls are on finite writer/bridge threads. */
public final class PrivateFiles {
    private static final Map<String,Long> WRITTEN=new HashMap<>();
    private PrivateFiles() { }
    public static Qualification.Source qualification(Context context) {
        return () -> new File(context.getFilesDir(),"qualification.json");
    }
    public static void write(Context context,long generation,String name,JSONObject data) {
        if(!name.equals("capability.json") && !name.equals("receipt.json") && !name.equals("bridge-receipt.json"))
            throw new IllegalArgumentException("receipt_name");
        final String payload=data.toString();
        new Thread(()->{
            synchronized(WRITTEN) {
                Long previous=WRITTEN.get(name);
                if(previous!=null && previous>generation)return;
                AtomicFile file=new AtomicFile(new File(context.getFilesDir(),name));
                FileOutputStream stream=null;
                try {
                    stream=file.startWrite();stream.write(payload.getBytes(StandardCharsets.UTF_8));
                    file.finishWrite(stream);WRITTEN.put(name,generation);
                } catch(Exception ignored) { if(stream!=null)file.failWrite(stream); }
            }
        },"NaszTV-voice-receipt").start();
    }
}
