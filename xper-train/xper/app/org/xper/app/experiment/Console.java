package org.xper.app.experiment;


import javax.swing.UIManager;

import org.springframework.config.java.context.JavaConfigApplicationContext;
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
				FileUtil.loadConfigClass("experiment.config_class"));
		ExperimentConsole console = context.getBean(ExperimentConsole.class);
		console.run();
	}
}
