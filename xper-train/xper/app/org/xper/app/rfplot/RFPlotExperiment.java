package org.xper.app.rfplot;


import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.experiment.ExperimentRunner;
import org.xper.rfplot.RFPlotConfig;
import org.xper.util.FileUtil;

public class RFPlotExperiment {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("rfplot.config_class", RFPlotConfig.class));
		ExperimentRunner runner = context.getBean(ExperimentRunner.class);
		runner.run();
	}
}
