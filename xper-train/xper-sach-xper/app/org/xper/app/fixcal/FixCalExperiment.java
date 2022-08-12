package org.xper.app.fixcal;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.config.FixCalConfig;
import org.xper.experiment.ExperimentRunner;
import org.xper.util.FileUtil;

public class FixCalExperiment {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("fixcal.config_class", FixCalConfig.class));
		ExperimentRunner runner = (ExperimentRunner) context
				.getBean(ExperimentRunner.class);
		runner.run();
	}
}
