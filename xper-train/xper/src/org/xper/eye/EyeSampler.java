package org.xper.eye;

import org.xper.drawing.Coordinates2D;
import org.xper.experiment.Threadable;
import org.xper.eye.strategy.EyeInStrategy;
import org.xper.eye.vo.EyePosition;

public interface EyeSampler extends Threadable {
	public boolean isIn(EyeInStrategy strategy, Coordinates2D eyeWinCenter, double eyeWinSize);
	public EyePosition getEyePositions();
}
