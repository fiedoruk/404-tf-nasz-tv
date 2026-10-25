package pl.local.nasztv.voiceassist;

import android.os.Bundle;
import android.service.voice.VoiceInteractionSession;
import android.service.voice.VoiceInteractionSessionService;

public final class SessionService extends VoiceInteractionSessionService {
    @Override public VoiceInteractionSession onNewSession(Bundle args) {
        return new AssistSession(this);
    }
}
