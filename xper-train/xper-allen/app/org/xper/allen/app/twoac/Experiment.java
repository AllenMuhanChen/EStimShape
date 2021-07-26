package org.xper.allen.app.twoac;


import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.experiment.ExperimentRunner;
import org.xper.util.FileUtil;
import org.xper.allen.experiment.twoac.ChoiceInRFTrialExperiment;
import org.xper.allen.experiment.twoac.TwoACMarkEveryStepTrialDrawingController;

public class Experiment {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));
		ExperimentRunner runner = context.getBean(ExperimentRunner.class);
		runner.run();
	}
}
