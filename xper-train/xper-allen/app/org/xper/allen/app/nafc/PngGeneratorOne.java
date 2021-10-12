package org.xper.allen.app.nafc;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.PngBlockGenOne;
import org.xper.util.FileUtil;

/**
 * Main function for reading an XML file of stimuli specifications and inputs them into the database. 
 * @param file path for xml file
 */
public class PngGeneratorOne {
	public static void main(String[] args) {
		// args 0 - numTrials
		// args 1 - numChoices
		// args 2-3 imageSize widthxheight
		// args 4-5 radius limits for sample
		int numTrials = Integer.parseInt(args[0]);
		int numChoices = Integer.parseInt(args[1]);
		double width = Double.parseDouble(args[2]);
		double height = Double.parseDouble(args[3]);
		double radiusLowerLim = Double.parseDouble(args[4]);
		double radiusUpperLim = Double.parseDouble(args[5]);
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		PngBlockGenOne gen = context.getBean(PngBlockGenOne.class);
		
		try {
			//target eye window size
			gen.toString();
			gen.generate(numTrials, numChoices, width, height, radiusLowerLim, radiusUpperLim);
			
		}
		catch(Exception e) {
			System.out.println("Something went wrong");
			e.printStackTrace();
		

		}
	}
}
