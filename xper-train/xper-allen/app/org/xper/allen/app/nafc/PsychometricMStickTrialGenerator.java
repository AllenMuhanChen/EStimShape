package org.xper.allen.app.nafc;

import java.util.Arrays;
import java.util.List;
import java.util.ListIterator;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NoiseChances;
import org.xper.allen.nafc.blockgen.NoisyMStickPngRandBlockGen;
import org.xper.allen.nafc.blockgen.SampleDistance;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.util.FileUtil;

public class PsychometricMStickTrialGenerator extends TrialGenerator{
	public static void main(String[] args) {
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		PsychometricBlockGen gen = context.getBean(PsychometricBlockGen.class);
		
		try {
			List<String> argsList = Arrays.asList(args);
			ListIterator<String> iterator = argsList.listIterator();
			
			int numPsychometricTrialsPerImage = Integer.parseInt(iterator.next());
			int numRandTrials = Integer.parseInt(iterator.next());
			double[][] noiseChances = stringToTupleArray(iterator.next());
			double[] noiseChancesFrequencies = stringToDoubleArray(iterator.next());
			double sampleDistanceLowerLim = Double.parseDouble(iterator.next());
			double sampleDistanceUpperLim = Double.parseDouble(iterator.next());
			double choiceDistanceLowerLim = Double.parseDouble(iterator.next());
			double choiceDistanceUpperLim = Double.parseDouble(iterator.next());
			double sampleScale = Double.parseDouble(iterator.next());
			double eyeWinSize = Double.parseDouble(iterator.next());
			
			
			gen.generate(numPsychometricTrialsPerImage, numRandTrials, new NoiseChances(noiseChances, noiseChancesFrequencies),
					new SampleDistance(sampleDistanceLowerLim, sampleDistanceUpperLim), new Lims(choiceDistanceLowerLim, choiceDistanceUpperLim), 
					sampleScale, eyeWinSize);
		}
		
		catch(Exception e) {
			e.printStackTrace();
			System.out.println("Failed to generate trials");
		}
	}
}
