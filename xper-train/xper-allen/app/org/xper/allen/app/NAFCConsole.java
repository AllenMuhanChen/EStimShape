package org.xper.allen.app;


import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.console.NAFCExperimentConsole;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;

public class NAFCConsole {
	public static void main(String[] args) {

		try {
			UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
		} catch (Exception e) {
			throw new XGLException(e);
		}
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.config_class"));
		NAFCExperimentConsole console = context.getBean(NAFCExperimentConsole.class);
		console.run();
	}
}