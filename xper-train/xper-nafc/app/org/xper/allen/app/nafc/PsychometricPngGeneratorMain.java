package org.xper.allen.app.nafc;

import java.util.Arrays;
import java.util.List;
import java.util.ListIterator;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricImageSetGenerator;
import org.xper.util.FileUtil;

/**
 * args:
 * 1. Number of sets of stimuli
 * 2. Stimuli per set
 * 3. Number of QM Categories per set
 * 4. Size (max)
 * @author r2_allen
 *
 */
public class PsychometricPngGeneratorMain {

	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		PsychometricBlockGen gen = context.getBean(PsychometricBlockGen.class);
		
		try {
			List<String> argsList = Arrays.asList(args);
			ListIterator<String> iterator = argsList.listIterator();
			
			int numSets = Integer.parseInt(iterator.next());
			int numPerSet = Integer.parseInt(iterator.next());
			double size = Double.parseDouble(iterator.next());
			double percentChangePosition = Double.parseDouble(iterator.next());
			int numRand = Integer.parseInt(iterator.next());
			
			for(int set=0; set<numSets; set++) {
				PsychometricImageSetGenerator imageSetGenerator = new PsychometricImageSetGenerator(gen);
				imageSetGenerator.generateImageSet(numPerSet, size, percentChangePosition, numRand);
			}
			
		} catch (Exception e) {
			e.printStackTrace();
		}
		
		
	}


}
