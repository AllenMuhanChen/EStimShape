package org.xper.allen.nafc.blockgen;

import static org.junit.Assert.*;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.NoisyMStickPngPsychometricBlockGen;
import org.xper.util.FileUtil;

public class NoisyMStickPngPsychometricBlockGenTest {

	@Test
	public void test() {
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));
		for (String s:context.getBeanDefinitionNames()) {
			System.out.println(s);
		}
		

		
	}

}
