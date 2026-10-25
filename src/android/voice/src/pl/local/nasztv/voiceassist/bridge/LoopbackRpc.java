package pl.local.nasztv.voiceassist.bridge;
import java.io.IOException;
import java.io.InputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.nio.channels.SocketChannel;
import java.nio.charset.StandardCharsets;

/** Nonblocking TCP only. Production endpoint is fixed loopback:9090; never DNS/HTTP. */
public final class LoopbackRpc {
    private final CancelToken token;
    private final JsonInput.Factory json;
    private final int port;
    private int calls;
    public LoopbackRpc(CancelToken token, JsonInput.Factory json) { this(token,json,9090); }
    LoopbackRpc(CancelToken token, JsonInput.Factory json, int fixturePort) {
        this.token=token;this.json=json;this.port=fixturePort;
    }
    public int calls() { return calls; }
    private void await(Selector selector, SelectionKey key, int operation, long deadline) throws IOException {
        key.interestOps(operation);
        while(true) {
            long remaining=token.remaining(deadline);
            if(selector.select(Math.max(1,remaining))>0) { selector.selectedKeys().clear();token.remaining(deadline);return; }
        }
    }
    public Object call(String request, String responseId, long deadline, boolean open) throws Exception {
        token.remaining(deadline);
        if(request.length()>2048)throw new IOException("request_size");
        calls++;
        try (Selector selector=Selector.open();SocketChannel channel=SocketChannel.open()) {
            token.attach(selector);
            try {
                channel.configureBlocking(false);
                SelectionKey key=channel.register(selector,SelectionKey.OP_CONNECT);
                boolean connected=channel.connect(new InetSocketAddress(InetAddress.getByAddress(new byte[]{127,0,0,1}),port));
                while(!connected) { await(selector,key,SelectionKey.OP_CONNECT,deadline);connected=channel.finishConnect(); }
                ByteBuffer bytes=ByteBuffer.wrap((request+"\n").getBytes(StandardCharsets.UTF_8));
                while(bytes.hasRemaining()) {
                    if(token.write(channel,bytes,deadline,open)==0)await(selector,key,SelectionKey.OP_WRITE,deadline);
                }
                InputStream input=new InputStream() {
                    @Override public int read() throws IOException { byte[] one=new byte[1];int n=read(one,0,1);return n<0?-1:one[0]&255; }
                    @Override public int read(byte[] b,int off,int len) throws IOException {
                        while(true) {
                            token.remaining(deadline);
                            int n=channel.read(ByteBuffer.wrap(b,off,len));
                            if(n!=0)return n;
                            await(selector,key,SelectionKey.OP_READ,deadline);
                        }
                    }
                };
                RpcFrames frames=new RpcFrames(input,()->token.remaining(deadline));
                final Object[] result=new Object[1];final int[] notifications={0};
                frames.readMatching(frame->{
                    Object decoded=RpcProtocol.response(frame,responseId,json);
                    if(decoded==RpcProtocol.NOTIFICATION) {
                        if(++notifications[0]>8)throw new IOException("notification_limit");return false;
                    }
                    result[0]=decoded;return true;
                });
                return result[0];
            } finally { token.detach(selector); }
        }
    }
}
