package org.xper.rfplot.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.renderer.AbstractRenderer;

import java.util.List;

public interface RFPlotDrawable {
	public void draw(Context context);
	public void setSpec(String spec);
	public void setDefaultSpec();
	public String getSpec();

	public List<Coordinates2D> getOutlinePoints(AbstractRenderer renderer);
}