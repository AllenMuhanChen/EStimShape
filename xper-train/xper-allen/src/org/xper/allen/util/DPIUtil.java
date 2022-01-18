package org.xper.allen.util;

import org.xper.Dependency;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.drawing.renderer.AbstractRenderer;

/**
 * Job is to take the monkey screen's DPI (dots per inch), and maximum stimulus size in degrees that is expected,
 *  in order to calculate
 * the bare minimum pixel resolution that would achieve at least that DPI at the maximum stimulus size. 
 * 
 * @author Allen Chen
 *
 */
public class DPIUtil {
	@Dependency
	double dpi;
	@Dependency
	double maxImageDimensionDegrees;
	@Dependency
	AbstractRenderer renderer;
	
	public int calculateMinResolution(){
		double maxDimMm = renderer.deg2mm(maxImageDimensionDegrees);
		double maxDimInches = maxDimMm / 25.4;
		int minPixels = (int) Math.round(dpi*maxDimInches);
		
		return minPixels;
	}

	public double getDpi() {
		return dpi;
	}

	public void setDpi(double dpi) {
		this.dpi = dpi;
	}

	public double getMaxStimulusDimensionDegrees() {
		return maxImageDimensionDegrees;
	}

	public void setMaxStimulusDimensionDegrees(double maxStimulusDimensionDegrees) {
		this.maxImageDimensionDegrees = maxStimulusDimensionDegrees;
	}

	public AbstractRenderer getRenderer() {
		return renderer;
	}

	public void setRenderer(AbstractRenderer renderer) {
		this.renderer = renderer;
	}
}
