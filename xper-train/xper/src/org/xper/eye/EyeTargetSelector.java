package org.xper.eye;

import org.xper.drawing.Coordinates2D;

public interface EyeTargetSelector {
	/**
	 * Return index of target selected. 0 based.
	 * @param targetCenter
	 * @param targetWinSize
	 * @param timeTarget in micro seconds.
	 * @return
	 */
	public int waitInitialSelection(Coordinates2D targetCenter [], double targetWinSize[], long timeTarget);
	public boolean waitEyeHold (int which, long timeTarget);
}
