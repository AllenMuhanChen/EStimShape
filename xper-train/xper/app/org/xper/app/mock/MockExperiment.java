package org.xper.app.mock;



import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.mockxper.MockXper;
import org.xper.util.FileUtil;

public class MockExperiment {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("mock.config_class", MockAppConfig.class));
		System.out.println("Start.");
		final MockXper xper = context.getBean(MockXper.class);
		Runtime.getRuntime().addShutdownHook(new Thread() {
			public void run() {
				xper.stop();
			}
		});
		xper.run();
	}
}
