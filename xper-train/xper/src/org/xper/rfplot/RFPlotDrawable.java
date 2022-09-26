package org.xper.rfplot;

import org.xper.drawing.Context;

public interface RFPlotDrawable {
	public void draw(Context context);
	public void setSpec (String spec);
	public void setDefaultSpec();

	public String getSpec();
}
