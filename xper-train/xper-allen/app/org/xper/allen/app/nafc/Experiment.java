package org.xper.allen.app.nafc;


import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.experiment.RewardButtonExperimentRunner;
import org.xper.experiment.ExperimentRunner;
import org.xper.util.FileUtil;

public class Experiment {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.config_class"));
		RewardButtonExperimentRunner runner = context.getBean(RewardButtonExperimentRunner.class);
		runner.run();
	}
}
