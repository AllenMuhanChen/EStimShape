package org.xper.allen.app.twoac;


import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.twoac.ChoiceInRFTrialExperiment;
import org.xper.allen.twoac.TwoACMarkEveryStepTrialDrawingController;
import org.xper.experiment.ExperimentRunner;
import org.xper.util.FileUtil;

public class Experiment {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));
		ExperimentRunner runner = context.getBean(ExperimentRunner.class);
		runner.run();
	}
}
