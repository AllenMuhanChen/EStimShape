package org.xper.allen.app.nafc;

import java.util.Arrays;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.PngBlockGen;
import org.xper.util.FileUtil;

/**
 * callMain function for reading an XML file of stimuli specifications and inputs them into the database.
 * @param file path for xml file
 */
public class PngGenerator {
	public static void main(String[] args) {
		// args 0     Trial Types (number of choices) in a comma delimited list
		// args 1     Number of Trial types in a comma delimited list. 
		// args 2-3   imageSize widthxheight
		// args 4-5   radius limits for sample
		// args 6     eyeWinSize
		// args 7-8   radius limits for choice
		// args 9-10  alpha for distractors (lower-upper limit)
		// args 11-12 extra distance distractors are from their default location (lower-upper limit)
		// args 13-14 distractor size scale (lower-upper limit)
		
		//int numSingleChoiceTrials = Integer.parseInt(args[0]);
		//int numDoubleChoiceTrials = Integer.parseInt(args[1]);
		
		//TRIAL TYPES
		String[] trialStrArray = args[0].split(",");
		
		int numTrialTypes = trialStrArray.length;
		int[] trialTypes = new int[numTrialTypes];
		for(int i=0; i<numTrialTypes;i++){
			trialTypes[i] = Integer.parseInt(trialStrArray[i]);
		}
		
		String[] trialNumStrArray = args[1].split(",");
		int[] trialTypeNums = new int[numTrialTypes];
		for(int i=0; i<numTrialTypes;i++){
			trialTypeNums[i] = Integer.parseInt(trialNumStrArray[i]);
		}
		double width = Double.parseDouble(args[2]);
		double height = Double.parseDouble(args[3]);
		double sampleRadiusLowerLim = Double.parseDouble(args[4]);
		double sampleRadiusUpperLim = Double.parseDouble(args[5]);
		double eyeWinSize = Double.parseDouble(args[6]);
		double choiceRadiusLowerLim = Double.parseDouble(args[7]);
		double choiceRadiusUpperLim = Double.parseDouble(args[8]);
		double alphaLowerLim = Double.parseDouble(args[9]);
		double alphaUpperLim = Double.parseDouble(args[10]);
		double distractorDistanceLowerLim = Double.parseDouble(args[11]);
		double distractorDistanceUpperLim = Double.parseDouble(args[12]);
		double distractorScaleLowerLim = Double.parseDouble(args[13]);
		double distractorScaleUpperLim = Double.parseDouble(args[14]);
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		PngBlockGen gen = context.getBean(PngBlockGen.class);
		
		try {
			//target eye window size
			gen.toString();
			gen.generate(trialTypes, trialTypeNums, width,
					height, sampleRadiusLowerLim, sampleRadiusUpperLim, 
					eyeWinSize, choiceRadiusLowerLim, choiceRadiusUpperLim, 
					alphaLowerLim, alphaUpperLim, distractorDistanceLowerLim,
					distractorDistanceUpperLim, distractorScaleLowerLim,
					distractorScaleUpperLim);
			
		}
		catch(Exception e) {
			System.out.println("Something went wrong");
			e.printStackTrace();
		

		}
	}
}
