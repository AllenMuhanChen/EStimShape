package org.xper.allen.app.nafc;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.*;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.util.FileUtil;

public class PsychometricBlockGeneratorMain extends TrialGenerator {

	public static void main(String[] args) {
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		PsychometricBlockGen gen = context.getBean(PsychometricBlockGen.class);

		try {
			PsychometricBlockGenInputTranslator translator = new PsychometricBlockGenInputTranslator(gen);
			gen.setUp(translator.translate(args));
			gen.generate();
		} catch (Exception e) {
			e.printStackTrace();
			System.out.println("Failed to generate trials");
		}
	}


}
