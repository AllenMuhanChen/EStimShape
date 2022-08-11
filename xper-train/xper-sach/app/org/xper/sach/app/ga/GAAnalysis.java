package org.xper.sach.app.ga;

import org.springframework.config.java.context.JavaConfigApplicationContext;
//import org.xper.sach.expt.behavior.SachExptConfig;
import org.xper.sach.analysis.GAAnalysisFrame;
import org.xper.util.FileUtil;


public class GAAnalysis {
	
	public static void main(String[] args) 
	{
		System.out.println("Start Data analysis frame:");
		//JavaConfigApplicationContext context = new JavaConfigApplicationContext(SachExptConfig.class);
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("experiment.ga.config_class"));
		
		GAAnalysisFrame anal = context.getBean(GAAnalysisFrame.class);
		anal.showBehavAnalysisFrame();
		
	}

}
	
