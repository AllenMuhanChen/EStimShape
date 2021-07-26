package org.xper.allen.specs;

import org.xper.drawing.Coordinates2D;

public class EStimSpecSpec extends SaccadeStimSpecSpec {

	public EStimSpecSpec(Coordinates2D targetEyeWinCoords, double targetEyeWinSize, double duration, long[] eStimObjData, long taskid) {
		this.targetEyeWinCoords = targetEyeWinCoords;
		this.targetEyeWinSize = targetEyeWinSize;
		this.duration = duration;
		this.eStimObjData = eStimObjData;
		
	}
}
