package org.xper.eye;

import org.xper.drawing.Coordinates2D;
import org.xper.eye.win.EyeWindowAlgorithm;

public interface EyeMonitor {

	public Coordinates2D getEyeWinCenter();

	public void setEyeWinCenter(Coordinates2D eyeWinCenter);

	public EyeWindowAlgorithm getEyeWindowAlgorithm();

}
