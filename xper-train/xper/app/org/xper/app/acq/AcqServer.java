package org.xper.app.acq;



import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.acq.SocketDataAcqServer;
import org.xper.config.AcqConfig;
import org.xper.util.FileUtil;

public class AcqServer {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("acq.config_class", AcqConfig.class));
		
		final SocketDataAcqServer server = context.getBean(SocketDataAcqServer.class);
		
		Runtime.getRuntime().addShutdownHook(new Thread() {
			public void run() {
				server.shutdown();
			}
		});

		server.run();
		
		System.exit(0);
	}
}
