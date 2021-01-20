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
		System.out.println("Attempting to get experiment");
		ChoiceInRFTrialExperiment exp = (ChoiceInRFTrialExperiment)runner.getExperiment();
		System.out.println("Attempting to get controller");
		TwoACMarkEveryStepTrialDrawingController controller = (TwoACMarkEveryStepTrialDrawingController) exp.getStateObject().getDrawingController();
		System.out.println("Attempting to get taskScene");
		System.out.println(controller.getTaskScene().getClass());
		runner.run();
	}
}
