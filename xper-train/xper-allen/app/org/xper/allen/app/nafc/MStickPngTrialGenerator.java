package org.xper.allen.app.nafc;

import java.util.Arrays;
import java.util.List;
import java.util.ListIterator;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.MStickPngBlockGen;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.util.FileUtil;

/**
 * callMain function for reading an XML file of stimuli specifications and inputs them into the database.
 * @param file path for xml file
 */
public class MStickPngTrialGenerator {
	public static void main(String[] args) {
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		MStickPngBlockGen gen = context.getBean(MStickPngBlockGen.class);

		try {

		} catch(Exception e) {
			System.out.println("Failed to load parameters for MStick Png experiment with frequency specification");
		}

		try {
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

			//target eye window size
			gen.generate(numDistractorTypes, numDistractorNumTrials,
					sampleScaleUpperLim, sampleRadiusLowerLim, sampleRadiusUpperLim, 
					eyeWinSize, choiceRadiusLowerLim, choiceRadiusUpperLim, 
					distractorDistanceLowerLim,
					distractorDistanceUpperLim,
					distractorScaleUpperLim, numMMCategories, numQMDistractorsTypes, numQMDistractorsNumTrials,
					numQMCategoriesTypes, numCategoriesMorphedNumTrials
					);

		}
		catch(Exception e) {
			e.printStackTrace();
			System.out.println("Failed to load parameters for MStick Png experiment with numTrial specification");
			
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
