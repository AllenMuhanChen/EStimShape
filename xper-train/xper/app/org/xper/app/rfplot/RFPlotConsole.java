package org.xper.app.rfplot;


import javax.swing.UIManager;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.console.ExperimentConsole;
import org.xper.exception.XGLException;
import org.xper.rfplot.RFPlotConfig;
import org.xper.util.FileUtil;

public class RFPlotConsole {
	public static void main(String[] args) {
		
		try {
			UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
		} catch (Exception e) {
			throw new XGLException(e);
		}
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("rfplot.config_class", RFPlotConfig.class));
		ExperimentConsole console = context.getBean(ExperimentConsole.class);
		
		console.run();
	}
}
