package org.xper.app.experiment.test;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.util.FileUtil;

public class RandGen {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.config_class"));

		RandomGeneration gen = context.getBean(RandomGeneration.class);
		gen.generate();
	}
}
