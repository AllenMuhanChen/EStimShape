package org.xper.sach.app.ga;


import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.experiment.ExperimentRunner;
import org.xper.util.FileUtil;

public class GAExperiment {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));
		ExperimentRunner runner = context.getBean(ExperimentRunner.class);
		runner.run();
	}
}
