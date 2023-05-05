package org.xper.classic;

import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialResult;
import org.xper.util.ThreadHelper;


public interface SlideTrialRunner {
	public TrialResult runTrial(SlideTrialExperimentState stateObject, ThreadHelper threadHelper);
}
