package org.xper.allen.app.nafc;

import java.util.Arrays;
import java.util.List;
import java.util.ListIterator;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.NoisyMStickPngBlockGen;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.util.FileUtil;

/**
 * Generates trials for a noisy mstick png training block. 
 * Parameters such as number of distractors, number of QM vs rand distractors,
 * noise parameters, etc...
 * are all specified as pairs of types and frequency/numTrials.
 * 
 * i.e for number of distractors:
 * types: {1,2,3} # of distractors per trial
 * frequency: {0.3, 0.5, 0.2} #frequency 
 * @author r2_allen
 *
 */
public class NoisyMStickPngGenerator {
	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		NoisyMStickPngBlockGen gen = context.getBean(NoisyMStickPngBlockGen.class);
		
		try { //try to generate trials with type-frequency pair inputs
			//Convert String[] args to List and use iterator to go through elements
			//using iterator allows for easily adding / rearranging elements without having to
			//	manually update every single index. 
			List<String> argsList = Arrays.asList(args);
			ListIterator<String> iterator = argsList.listIterator();
			
			int numTrials = Integer.parseInt(iterator.next());
			Integer[] numDistractorTypes = stringToIntegerArray(iterator.next());
			double[] numDistractorNumFrequencies= stringToDoubleArray(iterator.next());
			double sampleScaleUpperLim = Double.parseDouble(iterator.next());
			double sampleRadiusLowerLim = Double.parseDouble(iterator.next());
			double sampleRadiusUpperLim = Double.parseDouble(iterator.next());
			double eyeWinSize = Double.parseDouble(iterator.next());
			double choiceRadiusLowerLim = Double.parseDouble(iterator.next());
			double choiceRadiusUpperLim = Double.parseDouble(iterator.next());
			double distractorDistanceLowerLim = Double.parseDouble(iterator.next());
			double distractorDistanceUpperLim = Double.parseDouble(iterator.next());
			double distractorScaleUpperLim = Double.parseDouble(iterator.next());
			int numMMCategories = Integer.parseInt(iterator.next());
			Integer[] numQMDistractorsTypes = stringToIntegerArray(iterator.next());
			double[] numQMDistractorsFrequencies= stringToDoubleArray(iterator.next());
			Integer[] numQMCategoriesTypes = stringToIntegerArray(iterator.next());
			double[] numCategoriesMorphedFrequencies = stringToDoubleArray(iterator.next());
			NoiseType[] noiseTypes = stringToNoiseTypeArray(iterator.next());
			double[] noiseTypeFrequencies= stringToDoubleArray(iterator.next());
			double[][] noiseChancesTypes = stringToTupleArray(iterator.next());
			double[] noiseChancesFrequencies = stringToDoubleArray(iterator.next());
			

			//target eye window size
			gen.toString();
			gen.generate(numTrials, numDistractorTypes, numDistractorNumFrequencies,
					sampleScaleUpperLim, sampleRadiusLowerLim, sampleRadiusUpperLim, 
					eyeWinSize, choiceRadiusLowerLim, choiceRadiusUpperLim, 
					 distractorDistanceLowerLim,
					distractorDistanceUpperLim,
					distractorScaleUpperLim, numMMCategories, numQMDistractorsTypes, numQMDistractorsFrequencies,
					numQMCategoriesTypes, numCategoriesMorphedFrequencies,
					noiseTypes, noiseTypeFrequencies,
					noiseChancesTypes, noiseChancesFrequencies);
			return;
		} catch (Exception e) {
			System.out.println("Failed to load parameters for Noisy MStick PNG experiment with frequency specification.");
		}
		try { //try to generate trials with type-numTrials pair input
			//Convert String[] args to List as use iterator to go through elements
			List<String> argsList = Arrays.asList(args);
			ListIterator<String> iterator = argsList.listIterator();
			
			Integer[] numDistractorTypes = stringToIntegerArray(iterator.next());
			int[] numDistractorNumTrials = stringToIntArray(iterator.next());
			double sampleScaleUpperLim = Double.parseDouble(iterator.next());
			double sampleRadiusLowerLim = Double.parseDouble(iterator.next());
			double sampleRadiusUpperLim = Double.parseDouble(iterator.next());
			double eyeWinSize = Double.parseDouble(iterator.next());
			double choiceRadiusLowerLim = Double.parseDouble(iterator.next());
			double choiceRadiusUpperLim = Double.parseDouble(iterator.next());
			double distractorDistanceLowerLim = Double.parseDouble(iterator.next());
			double distractorDistanceUpperLim = Double.parseDouble(iterator.next());
			double distractorScaleUpperLim = Double.parseDouble(iterator.next());
			int numMMCategories = Integer.parseInt(iterator.next());
			Integer[] numQMDistractorsTypes = stringToIntegerArray(iterator.next());
			int[] numQMDistractorsNumTrials = stringToIntArray(iterator.next());
			Integer[] numQMCategoriesTypes = stringToIntegerArray(iterator.next());
			int[] numCategoriesMorphedNumTrials = stringToIntArray(iterator.next());
			NoiseType[] noiseTypes = stringToNoiseTypeArray(iterator.next());
			int[] noiseTypeNumTrials = stringToIntArray(iterator.next());
			double[][] noiseChancesTypes = stringToTupleArray(iterator.next());
			int[] noiseChancesNumTrials = stringToIntArray(iterator.next());
			

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
			return;
		}
		catch(Exception e) {
			System.out.println("Failed to load parameters for Noisy MStick PNG NAFC with numTrials specification");
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
