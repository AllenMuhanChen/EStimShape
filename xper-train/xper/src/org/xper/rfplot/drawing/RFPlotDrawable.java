package org.xper.rfplot.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;

public interface RFPlotDrawable {
	public void draw(Context context);
	public void setSpec (String spec);
	public void setDefaultSpec();
	public String getSpec();

	public void projectCoordinates(Coordinates2D mouseCoordinates);
}