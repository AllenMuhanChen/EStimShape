package org.xper.sach.app.ga;


import javax.swing.UIManager;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.console.ExperimentConsole;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

public class GAConsole {
	public static void main(String[] args) {
		
		try {
			UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
		} catch (Exception e) {
			throw new XGLException(e);
		}
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));
		ExperimentConsole console = context.getBean(ExperimentConsole.class);
//		console.setCanvasScaleFactor(4);
		console.run();
	}
}
