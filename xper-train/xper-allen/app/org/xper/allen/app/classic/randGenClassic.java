package org.xper.allen.app.classic;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.app.classic.randGenerationClassic;
import org.xper.util.FileUtil;

public class randGenClassic {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.config_class"));

		randGenerationClassic gen = context.getBean(randGenerationClassic.class);
		gen.generate();
	}
}
