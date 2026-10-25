package pl.local.nasztv.voiceassist;

import android.content.Intent;
import android.os.RemoteException;
import android.speech.RecognitionService;
import android.speech.SpeechRecognizer;

/** Required metadata component. Never records/proxies and is never our STT target. */
public final class MetadataRecognitionService extends RecognitionService {
    @Override protected void onStartListening(Intent intent, Callback callback) {
        try { callback.error(SpeechRecognizer.ERROR_CLIENT); } catch (RemoteException ignored) { }
    }
    @Override protected void onStopListening(Callback callback) {
        try { callback.error(SpeechRecognizer.ERROR_CLIENT); } catch (RemoteException ignored) { }
    }
    @Override protected void onCancel(Callback callback) { }
}
