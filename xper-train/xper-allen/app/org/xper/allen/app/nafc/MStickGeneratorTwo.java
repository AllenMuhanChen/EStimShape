package org.xper.allen.app.nafc;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.MStickPngBlockGenOne;
import org.xper.allen.nafc.blockgen.MStickPngBlockGenTwo;
import org.xper.util.FileUtil;

/**
 * Main function for reading an XML file of stimuli specifications and inputs them into the database. 
 * @param file path for xml file
 */
public class MStickGeneratorTwo {
	public static void main(String[] args) {
		// args 0     Trial Types (number of choices) in a comma delimited list
		// args 1     Number of Trial types in a comma delimited list. 
		// args 2-3   image size limits: minimum, maximum in degrees (diameter of bounding circle)
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
		double sampleScaleUpperLim = Double.parseDouble(args[2]);
		double sampleRadiusLowerLim = Double.parseDouble(args[3]);
		double sampleRadiusUpperLim = Double.parseDouble(args[4]);
		double eyeWinSize = Double.parseDouble(args[5]);
		double choiceRadiusLowerLim = Double.parseDouble(args[6]);
		double choiceRadiusUpperLim = Double.parseDouble(args[7]);
		double distractorDistanceLowerLim = Double.parseDouble(args[8]);
		double distractorDistanceUpperLim = Double.parseDouble(args[9]);
		double distractorScaleUpperLim = Double.parseDouble(args[10]);
		double metricMorphMagnitude = Double.parseDouble(args[11]);
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		MStickPngBlockGenTwo gen = context.getBean(MStickPngBlockGenTwo.class);
		
		try {
			//target eye window size
			gen.toString();
			gen.generate(trialTypes, trialTypeNums,
					sampleScaleUpperLim, sampleRadiusLowerLim, sampleRadiusUpperLim, 
					eyeWinSize, choiceRadiusLowerLim, choiceRadiusUpperLim, 
					 distractorDistanceLowerLim,
					distractorDistanceUpperLim,
					distractorScaleUpperLim, metricMorphMagnitude);
			
		}
		catch(Exception e) {
			System.out.println("Something went wrong");
			e.printStackTrace();
		

		}
	}
}
