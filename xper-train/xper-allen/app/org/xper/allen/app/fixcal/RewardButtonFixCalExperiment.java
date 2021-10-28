package org.xper.allen.app.fixcal;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.config.RewardButtonFixCalConfig;
import org.xper.allen.nafc.experiment.RewardButtonExperimentRunner;
import org.xper.experiment.ExperimentRunner;
import org.xper.util.FileUtil;

public class RewardButtonFixCalExperiment {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("fixcal.config_class", RewardButtonFixCalConfig.class));
		RewardButtonExperimentRunner runner = (RewardButtonExperimentRunner) context
				.getBean(RewardButtonExperimentRunner.class);
		runner.run();
	}
}
