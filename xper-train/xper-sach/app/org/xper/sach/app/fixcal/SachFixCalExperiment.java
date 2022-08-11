package org.xper.sach.app.fixcal;


import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.experiment.ExperimentRunner;
import org.xper.util.FileUtil;

public class SachFixCalExperiment {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("fixcal.config_class"));
		ExperimentRunner runner = (ExperimentRunner) context.getBean(ExperimentRunner.class);
		runner.run();
	}
}
