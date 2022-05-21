package org.xper.allen.app.nafc;

import java.util.Arrays;
import java.util.List;
import java.util.ListIterator;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.NoisyMStickPngPsychometricBlockGen;
import org.xper.allen.nafc.blockgen.NoisyMStickPngRandBlockGen;
import org.xper.util.FileUtil;

public class PsychometricMStickTrialGenerator extends TrialGenerator{
	public static void main(String[] args) {
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		NoisyMStickPngPsychometricBlockGen gen = context.getBean(NoisyMStickPngPsychometricBlockGen.class);

		try {
			List<String> argsList = Arrays.asList(args);
			ListIterator<String> iterator = argsList.listIterator();
			
			int trialsPerStim = Integer.parseInt(iterator.next());
			double[][] noiseChances = stringToTupleArray(iterator.next());
			double[] noiseChancesFrequencies = stringToDoubleArray(iterator.next());
			
			gen.generateTrials(trialsPerStim, noiseChances, noiseChancesFrequencies);
		}
		catch(Exception e) {
			e.printStackTrace();
			System.out.println("Failed to generate trials");
		}
	}
}
