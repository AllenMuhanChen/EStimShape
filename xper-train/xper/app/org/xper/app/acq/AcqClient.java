package org.xper.app.acq;



import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.acq.SocketDataAcqClient;
import org.xper.config.AcqConfig;
import org.xper.util.FileUtil;

public class AcqClient {

	/**
	 * @param args command to control acquisition server
	 */
	public static void main(String[] args) {
		if (args.length != 1) {
			printUsage();
			System.exit(0);
		}
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("acq.config_class", AcqConfig.class));

		SocketDataAcqClient client = context.getBean(SocketDataAcqClient.class);
		
		if (args[0].equalsIgnoreCase("connect")) {
			client.connect();
		} else if (args[0].equalsIgnoreCase("start")) {
			client.start();
		} else if (args[0].equalsIgnoreCase("stop")) {
			client.stop();
		} else if (args[0].equalsIgnoreCase("disconnect")) {
			client.disconnect();
		} else if (args[0].equalsIgnoreCase("shutdown")) {
			client.shutdown();
		} else {
			printUsage();
		}
		
		System.exit(0);
	}
	
	static void printUsage () {
		System.out.println ("Please specify command: connect, start, stop, disconnect, shutdown.");
	}
}
