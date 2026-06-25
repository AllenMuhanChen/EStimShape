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
	public String getOutputData();

	/**
	 * Whether this drawable is a 3-D object that must be positioned with a screen-space
	 * (post-projection) translation rather than a pre-projection world translation.
	 *
	 * Translating a 3-D object off the optical axis in world space under a perspective
	 * frustum shears it ("rotates with respect to the middle"), which both distorts the
	 * stimulus and invalidates its orthographic 2-D outline. Drawables that return true are
	 * rendered centered on the optical axis and slid into position after projection, matching
	 * how the experiment shows a pre-rendered (centered) stimulus translated as a flat image.
	 *
	 * Flat drawables (bars, gabors, images) are unaffected by perspective shear, so the
	 * default is false and they keep the original world-space translation.
	 */
	default boolean usesScreenSpaceTranslation() {
		return false;
	}
}