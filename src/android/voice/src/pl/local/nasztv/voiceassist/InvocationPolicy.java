package pl.local.nasztv.voiceassist;

/** AOSP Android14 show flags. Metadata about invocation, not proof of microphone routing. */
public final class InvocationPolicy {
    public static final int CONTEXT=1|2, GESTURE=4, PUSH_TO_TALK=32;
    private final long generation;
    private final int flags;
    private boolean claimed,cancelled;
    public InvocationPolicy(long generation,int flags) { this.generation=generation;this.flags=flags; }
    public int flags() { return flags; }
    public boolean automaticEligible() { int source=flags & ~CONTEXT;return source==GESTURE || source==PUSH_TO_TALK; }
    public String source() {
        switch(flags & ~CONTEXT) {
            case GESTURE:return "assist_gesture";
            case PUSH_TO_TALK:return "push_to_talk";
            case 0:return "unspecified";
            case 8:return "application";
            case 16:return "activity";
            case 64:return "notification";
            case 128:return "automotive";
            default:return "mixed_or_unknown";
        }
    }
    public boolean claimed() { return claimed; }
    public void cancel() { cancelled=true; }
    public boolean claimStart(long currentGeneration,boolean shown,boolean started,boolean done) {
        if(currentGeneration!=generation || !shown || started || done || cancelled || claimed || !automaticEligible())return false;
        claimed=true;return true;
    }
    public boolean mayHide(long currentGeneration,boolean shown,boolean sttDone,boolean bridgeBusy,boolean cleanupConfirmed) {
        return currentGeneration==generation && shown && sttDone && !bridgeBusy && cleanupConfirmed && !cancelled;
    }
}
