package org.xper.allen.app.nafc;

import java.util.AbstractMap;
import java.util.Arrays;

import javax.vecmath.Tuple2d;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.NoisyMStickPngBlockGen;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.util.FileUtil;

/**
 * Main function for reading an XML file of stimuli specifications and inputs them into the database. 
 * @param file path for xml file
 */
public class NoisyMStickPngGenerator {
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
		Integer[] numDistractorTypes = stringToIntegerArray(args[0]);
		int[] numDistractorNumTrials = stringToIntArray(args[1]);
		double sampleScaleUpperLim = Double.parseDouble(args[2]);
		double sampleRadiusLowerLim = Double.parseDouble(args[3]);
		double sampleRadiusUpperLim = Double.parseDouble(args[4]);
		double eyeWinSize = Double.parseDouble(args[5]);
		double choiceRadiusLowerLim = Double.parseDouble(args[6]);
		double choiceRadiusUpperLim = Double.parseDouble(args[7]);
		double distractorDistanceLowerLim = Double.parseDouble(args[8]);
		double distractorDistanceUpperLim = Double.parseDouble(args[9]);
		double distractorScaleUpperLim = Double.parseDouble(args[10]);
		int numMMCategories = Integer.parseInt(args[11]);
		Integer[] numQMDistractorsTypes = stringToIntegerArray(args[12]);
		int[] numQMDistractorsNumTrials = stringToIntArray(args[13]);
		Integer[] numQMCategoriesTypes = stringToIntegerArray(args[14]);
		int[] numCategoriesMorphedNumTrials = stringToIntArray(args[15]);
		NoiseType[] noiseTypes = stringToNoiseTypeArray(args[16]);
		int[] noiseTypeNumTrials = stringToIntArray(args[17]);
		double[][] noiseChancesTypes = stringToTupleArray(args[18]);
		int[] noiseChancesNumTrials = stringToIntArray(args[19]);
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		NoisyMStickPngBlockGen gen = context.getBean(NoisyMStickPngBlockGen.class);
		
		try {
			//target eye window size
			gen.toString();
			gen.generate(numDistractorTypes, numDistractorNumTrials,
					sampleScaleUpperLim, sampleRadiusLowerLim, sampleRadiusUpperLim, 
					eyeWinSize, choiceRadiusLowerLim, choiceRadiusUpperLim, 
					 distractorDistanceLowerLim,
					distractorDistanceUpperLim,
					distractorScaleUpperLim, numMMCategories, numQMDistractorsTypes, numQMDistractorsNumTrials,
					numQMCategoriesTypes, numCategoriesMorphedNumTrials,
					noiseTypes, noiseTypeNumTrials,
					noiseChancesTypes, noiseChancesNumTrials);
			
		}
		catch(Exception e) {
			System.out.println("Something went wrong");
			e.printStackTrace();
		

		}
	}
	
	public static Integer[] stringToIntegerArray(String string) {
		String[] strArr = string.split(",");
		int length = strArr.length;
		Integer[] intArr = new Integer[length];
		for(int i=0; i<length; i++) {
			intArr[i] = Integer.parseInt(strArr[i]);
		}
		return intArr;
	}
	
	public static int[] stringToIntArray(String string) {
		String[] strArr = string.split(",");
		int length = strArr.length;
		int[] intArr = new int[length];
		for(int i=0; i<length; i++) {
			intArr[i] = Integer.parseInt(strArr[i]);
		}
		return intArr;
	}
	
	public static double[] stringToDoubleArray(String string) {
		String[] strArr = string.split(",");
		int length = strArr.length;
		double[] doubleArr = new double[length];
		for(int i=0; i<length; i++) {
			doubleArr[i] = Double.parseDouble(strArr[i]);
		}
		return doubleArr;
	}
	
	public static NoiseType[] stringToNoiseTypeArray(String string) {
		String[] strArr = string.split(",");
		int length = strArr.length;
		NoiseType[] noiseTypeArr = new NoiseType[length];
		for(int i=0; i<length; i++) {
			noiseTypeArr[i] = NoiseType.valueOf(strArr[i]);
		}
		return noiseTypeArr;
	}
	
	/**
	 * "(0.5,1),(0.25,0.5),(0.75,1)" --> double[3][2] 
	 * 								 --> [0.5][1]
	 * 									 [0.25][0.5]
	 * 									 [0.75][1]
	 * @param string
	 * @return
	 */
	public static double[][] stringToTupleArray(String string) {
		String[] strArr = string.split("\\),");
		
		int length = strArr.length;
		double[][] noiseTypeArr = new double[length][2];
		for(int i=0; i<length; i++) {
			String removedParenthesis = strArr[i].replaceAll("\\(", "").replaceAll("\\)", "");
			
			String[] split = removedParenthesis.split(",");
			noiseTypeArr[i][0] = Double.parseDouble(split[0]);
			noiseTypeArr[i][1] = Double.parseDouble(split[1]);
		}
		return noiseTypeArr;
	}
}
