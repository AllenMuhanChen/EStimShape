package org.xper.allen.app.experiment.test;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.app.classic.randGenerationClassic;
import org.xper.util.FileUtil;

public class RandGenAllen {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		randGenerationClassic gen = context.getBean(randGenerationClassic.class);
		gen.generate();
	}
}
