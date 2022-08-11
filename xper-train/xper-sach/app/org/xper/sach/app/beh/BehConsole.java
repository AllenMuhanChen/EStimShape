package org.xper.sach.app.beh;



import javax.swing.UIManager;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.console.ExperimentConsole;
import org.xper.exception.XGLException;
import org.xper.sach.config.SachBehavConfig;
import org.xper.util.FileUtil;

public class BehConsole {
	public static void main(String[] args) {
		
		try {
			UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
		} catch (Exception e) {
			throw new XGLException(e);
		}
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.beh.config_class", SachBehavConfig.class));
		ExperimentConsole console = context.getBean(ExperimentConsole.class);
//		console.setCanvasScaleFactor(3);
		console.run();
	}
}
