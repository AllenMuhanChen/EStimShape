package org.xper.app.acq;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.config.AcqConfig;
import org.xper.time.SocketTimeServer;
import org.xper.util.FileUtil;

public class TimeServer {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("acq.config_class", AcqConfig.class));
		
		final SocketTimeServer server = context.getBean(SocketTimeServer.class);

		Runtime.getRuntime().addShutdownHook(new Thread() {
			public void run() {
				server.stop();
			}
		});

		server.run();
	}
}
