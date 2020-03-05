package org.xper.allen.app.specGenerators;

import java.util.ArrayList;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.util.FileUtil;

public class TrainingGenerator {
	public static void main(String[] args) {
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		trainingBlockGen gen = context.getBean(trainingBlockGen.class);
		
		try {
			//blockId
			String filepath = args[0];
			//target eye window size
			double targetEyeWinSize = Double.parseDouble(args[1]);
			gen.generate(filepath, targetEyeWinSize);
		}
		catch(Exception e) {
			System.out.println("Something went wrong");
			e.printStackTrace();
		

		}
	}
}
