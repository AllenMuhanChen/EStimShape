package org.xper.allen.nafc.experiment;

import org.xper.allen.nafc.vo.NAFCTrialResult;
import org.xper.util.ThreadHelper;

public interface NAFCTrialRunner{
	public NAFCTrialResult runTrial(NAFCExperimentState stateObject, ThreadHelper threadHelper);
}
