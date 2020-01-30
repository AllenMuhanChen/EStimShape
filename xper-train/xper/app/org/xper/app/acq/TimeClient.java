package org.xper.app.acq;



import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.config.AcqConfig;
import org.xper.time.SocketTimeClient;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;
import org.xper.util.FileUtil;

public class TimeClient {
	public static void main(String[] args) {
		
		TimeUtil timeUtil = new DefaultTimeUtil();

		int count = 1000;

		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("acq.config_class", AcqConfig.class));
		
		SocketTimeClient client = context.getBean(SocketTimeClient.class);
		
		System.out.println("Benchmarking Time Server ... ");

		long before = timeUtil.currentTimeMicros();
		for (int i = 0; i < count; i++) {
			client.currentTimeMicros();
		}
		long after = timeUtil.currentTimeMicros();

		System.out.println("Overhead: " + (double) (after - before)
				/ (double) count / 1000.0 + " milliseconds.");

		System.out.println("Current Time: " + client.currentTimeMicros()
				+ " microseconds.");
	}
}
