package org.xper.sach.app.beh;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.experiment.ExperimentRunner;
import org.xper.util.FileUtil;

public class BehExperiment {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.beh.config_class"));
		ExperimentRunner runner = context.getBean(ExperimentRunner.class);
		runner.run();
	}
}
