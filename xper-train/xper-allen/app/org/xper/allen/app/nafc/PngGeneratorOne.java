package org.xper.allen.app.nafc;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.PngBlockGenOne;
import org.xper.util.FileUtil;

/**
 * Main function for reading an XML file of stimuli specifications and inputs them into the database. 
 * @param file path for xml file
 */
public class PngGeneratorOne {
	public static void main(String[] args) {
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		PngBlockGenOne gen = context.getBean(PngBlockGenOne.class);
		
		try {
			//target eye window size
			gen.toString();
			gen.generate();
			
		}
		catch(Exception e) {
			System.out.println("Something went wrong");
			e.printStackTrace();
		

		}
	}
}
