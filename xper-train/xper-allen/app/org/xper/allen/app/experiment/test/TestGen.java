package org.xper.allen.app.experiment.test;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.app.experiment.test.TestGeneration;
import org.xper.util.FileUtil;

public class TestGen {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.config_class"));

		TestGeneration gen = context.getBean(TestGeneration.class);
		gen.generate();
	}
}
