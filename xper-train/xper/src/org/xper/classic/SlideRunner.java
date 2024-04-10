package org.xper.classic;

import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.classic.vo.TrialResult;
import org.xper.util.ThreadHelper;


public interface SlideRunner {
	public TrialResult runSlides(SlideTrialExperimentState stateObject, ThreadHelper threadHelper);
}