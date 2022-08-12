package org.xper.app.rds;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.experiment.ExperimentRunner;
import org.xper.rds.RdsConfig;
import org.xper.util.FileUtil;

public class RdsExperiment {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("rds.config_class", RdsConfig.class));
		ExperimentRunner runner = (ExperimentRunner) context
				.getBean(ExperimentRunner.class);
		runner.run();
	}
}
