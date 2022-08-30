package org.xper.allen.app.fixcal;



import javax.swing.UIManager;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.config.RewardButtonFixCalConfig;
import org.xper.allen.fixcal.RewardButtonExperimentConsole;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

public class RewardButtonFixCalConsole {
	public static void main(String[] args) {
		
		try {
			UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
		} catch (Exception e) {
			throw new XGLException(e);
		}
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("fixcal.config_class", RewardButtonFixCalConfig.class));
		RewardButtonExperimentConsole console = context.getBean(RewardButtonExperimentConsole.class);
		
		console.run();
	}
}
