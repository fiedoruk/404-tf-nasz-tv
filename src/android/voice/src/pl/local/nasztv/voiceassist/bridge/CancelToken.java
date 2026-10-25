package pl.local.nasztv.voiceassist.bridge;
import java.io.IOException;
import java.io.InterruptedIOException;
import java.nio.ByteBuffer;
import java.nio.channels.Selector;
import java.nio.channels.WritableByteChannel;

public final class CancelToken {
    private boolean cancelled;
    private Selector selector;
    private boolean openBytesWritten;
    public static long now() { return System.nanoTime()/1_000_000L; }
    public synchronized void cancel() {
        cancelled=true;
        if(selector!=null) try { selector.wakeup(); } catch(RuntimeException ignored) { }
    }
    public synchronized boolean cancelled() { return cancelled; }
    public synchronized boolean openBytesWritten() { return openBytesWritten; }
    public synchronized void attach(Selector next) throws IOException {
        if(cancelled)throw new InterruptedIOException("cancelled");selector=next;
    }
    public synchronized void detach(Selector old) { if(selector==old)selector=null; }
    public synchronized long remaining(long deadline) throws IOException {
        long remaining=deadline-now();
        if(cancelled || Thread.currentThread().isInterrupted()) throw new InterruptedIOException("cancelled");
        if(remaining<=0)throw new IOException("deadline");return remaining;
    }
    /** Atomic cancel-vs-write decision; channel MUST be nonblocking. Runs on the worker only. */
    public synchronized int write(WritableByteChannel channel, ByteBuffer bytes, long deadline, boolean open) throws IOException {
        remaining(deadline);
        int count=channel.write(bytes);
        if(open && count>0)openBytesWritten=true;
        return count;
    }
}
