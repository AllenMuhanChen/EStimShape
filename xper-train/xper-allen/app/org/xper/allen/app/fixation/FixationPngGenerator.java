package org.xper.allen.app.fixation;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.util.FileUtil;

public class FixationPngGenerator {
	public static void main(String[] args) {
		// args 0 - numTrials
		// args 1 - scale
		// args 2-3 radius Lower and Upper Lim
		int numTrials = Integer.parseInt(args[0]);
		double scale = Double.parseDouble(args[1]);
		double radiusLowerLim= Double.parseDouble(args[2]);
		double radiusUpperLim = Double.parseDouble(args[3]);

		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		FixationPngBlockGen gen = context.getBean(FixationPngBlockGen.class);

		try {
			//target eye window size
			gen.toString();
			gen.generate(numTrials, scale, radiusLowerLim, radiusUpperLim);

		}
		catch(Exception e) {
			System.out.println("Something went wrong");
			e.printStackTrace();


		}
	}
}
