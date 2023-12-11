package org.xper.allen.app;


import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.experiment.ExperimentRunner;
import org.xper.util.FileUtil;

public class FixationExperiment {
	public static void main(String[] args) {

		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.fixation.config_class"));
		ExperimentRunner runner = context.getBean(ExperimentRunner.class);
		runner.run();
	}
}