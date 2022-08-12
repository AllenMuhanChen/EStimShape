package org.xper.eye.win;

import org.xper.Dependency;


public class ConstantEyeWindowAlgorithm implements EyeWindowAlgorithm {
	@Dependency
	double eyeWinSize;

	public double getCurrentEyeWindowSize() {
		return eyeWinSize;
	}

	public double getNextEyeWindowSize() {
		return eyeWinSize;
	}

	public double getEyeWinSize() {
		return eyeWinSize;
	}

	public void setEyeWinSize(double eyeWinSize) {
		this.eyeWinSize = eyeWinSize;
	}

	public void resetEyeWindowSize() {
	}

}
