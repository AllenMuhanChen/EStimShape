package org.xper.allen.nafc;

import org.xper.allen.nafc.experiment.NAFCTrialContext;
import org.xper.drawing.Drawable;

public interface NAFCDrawable extends Drawable{
	public void draw (NAFCTrialContext context);
}
