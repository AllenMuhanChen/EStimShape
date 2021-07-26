package org.xper.allen.app.twoac;


import javax.swing.UIManager;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.experiment.saccade.console.SaccadeExperimentConsole;
import org.xper.allen.experiment.twoac.console.TwoACExperimentConsole;
import org.xper.console.ExperimentConsole;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

public class Console {
	public static void main(String[] args) {
		
		try {
			UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
		} catch (Exception e) {
			throw new XGLException(e);
		}
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));
		TwoACExperimentConsole console = context.getBean(TwoACExperimentConsole.class);
		console.run();
	}
}
