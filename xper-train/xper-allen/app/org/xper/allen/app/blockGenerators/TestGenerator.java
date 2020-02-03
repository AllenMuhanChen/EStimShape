package org.xper.allen.app.blockGenerators;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.xper.allen.config.AllenDbUtil;
import org.xper.app.experiment.test.RandomGeneration;
import org.xper.util.FileUtil;

public class TestGenerator {

	public static void main(String[] args) {

		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		sampleBlockGen gen = context.getBean(sampleBlockGen.class);
		gen.generate(1);

	}

}
