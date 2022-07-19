package org.xper.allen.app.nafc;

import java.util.ListIterator;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.*;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.allen.nafc.vo.NoiseForm;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.util.FileUtil;

public class PsychometricBlockGeneratorMain extends TrialGenerator{


	private static ListIterator<String> iterator;

	public static void main(String[] args) {
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		PsychometricBlockGen gen = context.getBean(PsychometricBlockGen.class);
		
		try {
			PsychometricBlockGenInputParser parser = new PsychometricBlockGenInputParser(gen);
			parser.parse(args);
			gen.generate();
		}
		
		catch(Exception e) {
			e.printStackTrace();
			System.out.println("Failed to generate trials");
		}
	}


}
