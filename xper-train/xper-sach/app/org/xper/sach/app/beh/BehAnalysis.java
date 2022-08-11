package org.xper.sach.app.beh;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.sach.analysis.BehavAnalysisFrame;
import org.xper.util.FileUtil;

public class BehAnalysis {
	public static void main(String[] args) {
		System.out.println("Start Data analysis frame:");
		
		// trying to separate analysis from other stuff so it can be run on mac (no comedi/ni drivers)
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.beh.anal_config_class"));
		
		BehavAnalysisFrame anal = context.getBean(BehavAnalysisFrame.class);	
		anal.showBehavAnalysisFrame();
	}
}
	
