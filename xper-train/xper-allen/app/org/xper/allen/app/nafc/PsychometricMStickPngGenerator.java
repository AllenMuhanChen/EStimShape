package org.xper.allen.app.nafc;

import java.util.Arrays;
import java.util.List;
import java.util.ListIterator;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.NoisyMStickPngPsychometricBlockGen;
import org.xper.allen.nafc.blockgen.NoisyMStickPngRandBlockGen;
import org.xper.allen.nafc.vo.NoiseType;
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
public class PsychometricMStickPngGenerator {
	
	

	public static void main(String[] args) {
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		NoisyMStickPngPsychometricBlockGen gen = context.getBean(NoisyMStickPngPsychometricBlockGen.class);
		
		try {
			List<String> argsList = Arrays.asList(args);
			ListIterator<String> iterator = argsList.listIterator();
			
			int numSets = Integer.parseInt(iterator.next());
			int numPerSet = Integer.parseInt(iterator.next());
			double size = Double.parseDouble(iterator.next());
		
			
			for(int set=0; set<numSets; set++) {
				gen.generateSet(numPerSet, size);
			}
			
		} catch (Exception e) {
			e.printStackTrace();
		}
		
		
	}


}
