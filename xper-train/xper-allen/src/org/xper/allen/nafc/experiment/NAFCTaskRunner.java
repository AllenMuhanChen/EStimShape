package org.xper.allen.nafc.experiment;

import org.xper.allen.nafc.vo.NAFCTrialResult;

public interface NAFCTaskRunner {
	public NAFCTrialResult runTask(NAFCExperimentState stateObject, NAFCTrialContext context);
}