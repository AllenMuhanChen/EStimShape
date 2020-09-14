package org.xper.allen.app.simpleestim;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.blockgen.SimpleEStimBlockGen;
import org.xper.allen.blockgen.TrainingBlockGen;
import org.xper.util.FileUtil;

public class SimpleEStimGenerator {
	public static void main(String[] args) {
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		SimpleEStimBlockGen gen = context.getBean(SimpleEStimBlockGen.class);
		
		try {
			//blockId
			String filepath = args[0];
			//target eye window size
			gen.generate(filepath);
		}
		catch(Exception e) {
			System.out.println("Something went wrong");
			e.printStackTrace();
		

		}
	}
}
