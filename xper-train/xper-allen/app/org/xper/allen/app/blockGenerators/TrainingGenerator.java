package org.xper.allen.app.blockGenerators;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.util.FileUtil;

public class TrainingGenerator {
	static int blockId = 5;
	public static void main(String[] args) {

		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		trainingBlockGen gen = context.getBean(trainingBlockGen.class);
		gen.generate(blockId);

	}
}
