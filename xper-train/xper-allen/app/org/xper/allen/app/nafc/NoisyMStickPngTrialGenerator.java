package org.xper.allen.app.nafc;

import java.util.Arrays;
import java.util.List;
import java.util.ListIterator;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.NoisyMStickPngRandBlockGen;
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
public class NoisyMStickPngTrialGenerator extends TrialGenerator{
	public static void main(String[] args) {

		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		NoisyMStickPngRandBlockGen gen = context.getBean(NoisyMStickPngRandBlockGen.class);

		try { //try to generate trials with type-frequency pair inputs
			//Convert String[] args to List and use iterator to go through elements
			//using iterator allows for easily adding / rearranging elements without having to
			//	manually update every single index. 
			List<String> argsList = Arrays.asList(args);
			ListIterator<String> iterator = argsList.listIterator();
			
			int numTrials = Integer.parseInt(iterator.next());
			Integer[] numDistractorTypes = stringToIntegerArray(iterator.next());
			double[] numDistractorFrequencies= stringToDoubleArray(iterator.next());
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
			double[] numQMCategoriesFrequencies = stringToDoubleArray(iterator.next());
			NoiseType[] noiseTypes = stringToNoiseTypeArray(iterator.next());
			double[] noiseTypeFrequencies= stringToDoubleArray(iterator.next());
			double[][] noiseChancesTypes = stringToTupleArray(iterator.next());
			double[] noiseChancesFrequencies = stringToDoubleArray(iterator.next());


			//target eye window size
			gen.toString();
			gen.generate(numTrials, numDistractorTypes, numDistractorFrequencies,
					sampleScaleUpperLim, sampleRadiusLowerLim, sampleRadiusUpperLim, 
					eyeWinSize, choiceRadiusLowerLim, choiceRadiusUpperLim, 
					distractorDistanceLowerLim,
					distractorDistanceUpperLim,
					distractorScaleUpperLim, numMMCategories, numQMDistractorsTypes, numQMDistractorsFrequencies,
					numQMCategoriesTypes, numQMCategoriesFrequencies,
					noiseTypes, noiseTypeFrequencies,
					noiseChancesTypes, noiseChancesFrequencies);
			return;
		} catch (Exception e) {
			e.printStackTrace();
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


	
}
