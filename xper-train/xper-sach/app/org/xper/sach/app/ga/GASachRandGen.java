package org.xper.sach.app.ga;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.sach.expt.generate.SachRandomGeneration;
import org.xper.util.FileUtil;

public class GASachRandGen {
	public static void main(String[] args) {
		
		// Class<?> c = FileUtil.loadConfigClass("experiment.ga.config_class");
		
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("experiment.ga.config_class"));

		SachRandomGeneration gen = context.getBean(SachRandomGeneration.class);
		gen.generateGA();
	}
}
 