package org.xper.app.rds;



import javax.swing.UIManager;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.console.ExperimentConsole;
import org.xper.exception.XGLException;
import org.xper.rds.RdsConfig;
import org.xper.util.FileUtil;

public class RdsConsole {
	public static void main(String[] args) {
		
		try {
			UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
		} catch (Exception e) {
			throw new XGLException(e);
		}
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("rds.config_class", RdsConfig.class));
		ExperimentConsole console = context.getBean(ExperimentConsole.class);
		
		console.run();
	}
}
