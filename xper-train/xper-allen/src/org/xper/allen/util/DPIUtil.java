package org.xper.allen.util;

import org.xper.Dependency;
import org.xper.drawing.renderer.AbstractRenderer;

/**
 * Job is to take the monkey screen's DPI (dots per inch), and maximum stimulus size in degrees that is expected,
 *  in order to calculate
 * the bare minimum pixel resolution that would achieve at least that DPI at the maximum stimulus size.
 *
 * Another functionality is to take the DPI of the monitor that the images are being generated on
 * and use this to calculate the size of the openGL window in mm so the images can be generated
 * properly.
 * @author Allen Chen
 *
 */
public class DPIUtil {
	@Dependency
	double generatorDPI;
	@Dependency
	double monkeyDPI;
	@Dependency
	double maxImageDimensionDegrees;
	@Dependency
	AbstractRenderer renderer;

	public double maxDimMm;
	public int calculateMinResolution(){
		maxDimMm = renderer.deg2mm(maxImageDimensionDegrees);
		double maxDimInches = maxDimMm / 25.4;
		int minPixels = (int) (monkeyDPI*maxDimInches) + 1;

		return minPixels;
	}

	public double calculateMmForRenderer() {
		int pixels = calculateMinResolution();
		//System.out.println(pixels * (1/generatorDPI) * 25.4);
		return (double) pixels * (1.0/generatorDPI) * 25.4;
	}

	public double getDpi() {
		return monkeyDPI;
	}

	public void setDpi(double dpi) {
		this.monkeyDPI = dpi;
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

	public double getGeneratorDPI() {
		return generatorDPI;
	}

	public void setGeneratorDPI(double generatorDPI) {
		this.generatorDPI = generatorDPI;
	}
}