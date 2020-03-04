package org.xper.allen.app.blockGenerators;

import java.util.ArrayList;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.util.FileUtil;

public class TrainingGenerator {
	public static void main(String[] args) {
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		trainingBlockGen gen = context.getBean(trainingBlockGen.class);
		
		try {
			//blockId
			int blockId = Integer.parseInt(args[0]);
			//visTypes
			String csvInput = args[1];
			String[] elements = csvInput.split(",");
			ArrayList<Integer> visualTypes = new ArrayList<Integer>();
			for (String s:elements) {
				visualTypes.add(Integer.parseInt(s));
			}
			//target eye window size
			int targetEyeWinSize = Integer.parseInt(args[2]);
			gen.generate(blockId, visualTypes, targetEyeWinSize);
		}
		catch(Exception e) {
			System.out.println("Not enough arguments were given. args[0]: int blockId, args[1]: visualTypes (comma separated list of StimObjIDs) ");
		
		

		}
	}
}
