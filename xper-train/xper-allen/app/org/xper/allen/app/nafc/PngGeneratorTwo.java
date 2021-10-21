package org.xper.allen.app.nafc;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.PngBlockGenOne;
import org.xper.allen.nafc.blockgen.PngBlockGenTwo;
import org.xper.util.FileUtil;

/**
 * Main function for reading an XML file of stimuli specifications and inputs them into the database. 
 * @param file path for xml file
 */
public class PngGeneratorTwo {
	public static void main(String[] args) {
		// args 0 - numTrials
		// args 1 - numChoices
		// args 2-3 imageSize widthxheight
		// args 4-5 radius limits for sample
		// args 6   eyeWinSize
		// args 7-8 radius limits for choice
		int numTrials = Integer.parseInt(args[0]);
		int numChoices = Integer.parseInt(args[1]);
		double width = Double.parseDouble(args[2]);
		double height = Double.parseDouble(args[3]);
		double sampleRadiusLowerLim = Double.parseDouble(args[4]);
		double sampleRadiusUpperLim = Double.parseDouble(args[5]);
		double eyeWinSize = Double.parseDouble(args[6]);
		double choiceRadiusLowerLim = Double.parseDouble(args[7]);
		double choiceRadiusUpperLim = Double.parseDouble(args[8]);
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		PngBlockGenTwo gen = context.getBean(PngBlockGenTwo.class);
		
		try {
			//target eye window size
			gen.toString();
			gen.generate(numTrials, numChoices, width, height, sampleRadiusLowerLim, sampleRadiusUpperLim, eyeWinSize, choiceRadiusLowerLim, choiceRadiusUpperLim);
			
		}
		catch(Exception e) {
			System.out.println("Something went wrong");
			e.printStackTrace();
		

		}
	}
}
