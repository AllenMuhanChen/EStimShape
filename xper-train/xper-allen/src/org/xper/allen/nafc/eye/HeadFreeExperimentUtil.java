package org.xper.allen.nafc.eye;

import org.xper.allen.nafc.experiment.NAFCExperimentState;
import org.xper.allen.nafc.experiment.NAFCExperimentUtil;
import org.xper.allen.nafc.vo.NAFCTrialResult;
import org.xper.util.ThreadHelper;

public class HeadFreeExperimentUtil{
	public static NAFCTrialResult getMonkeyFixation(NAFCExperimentState state, ThreadHelper threadHelper) {
		int fixationAttempts = 1;
		int maxFixationAttempts = 5;
		
		while(fixationAttempts < maxFixationAttempts) {
			NAFCTrialResult res = NAFCExperimentUtil.getMonkeyFixation(state, threadHelper); 
			if(res==NAFCTrialResult.FIXATION_SUCCESS) {
				return res;
			}
			fixationAttempts++;
			System.out.println("AC238490238: fixation attempts: " + fixationAttempts +  ": " + res.toString());
		}
		return NAFCExperimentUtil.getMonkeyFixation(state, threadHelper);
	}
}
