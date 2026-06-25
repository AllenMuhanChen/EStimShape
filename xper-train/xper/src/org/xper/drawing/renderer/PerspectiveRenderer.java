package org.xper.drawing.renderer;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;

/**
 * Modified by AC because was previously broken (would not display stimuli on rig 2). Remodelled
 * to operate more similarily to PerspectiveStereoRenderer which was working properly. Even if PerspectiveStereoRenderer
 * can be used for mono, xper will always be drawing two copies of the screen, which impacts performance.
 * This fix was important for economical dynamic noise generation.
 *
 * Critical lines that were changed to fix drawing was putting the bulk of the old init() into setup()
 * and calling setup() before each draw call.
 * @author r2_allen
 *
 */
public class PerspectiveRenderer extends AbstractRenderer {
	/**
	 * Optional override for the near clipping plane distance (mm from the eye). When null the
	 * shared {@link AbstractRenderer#PROJECTION_NEAR} is used. Pulling the near plane out toward
	 * the screen plane (and tightening the far plane via {@code depth}) dramatically improves
	 * depth-buffer precision for 3-D stimuli that sit ~{@code distance} mm away, which matters on
	 * windows created with a low-bit-depth depth buffer. It does NOT change the mm-to-degree
	 * mapping or where anything projects in x/y (the frustum extents scale with the near plane,
	 * so the near factor cancels).
	 */
	private Double customNearPlaneDistance = null;

	public PerspectiveRenderer() {
	}

	public void init() {
		super.init();
	}

	public Double getCustomNearPlaneDistance() {
		return customNearPlaneDistance;
	}

	public void setCustomNearPlaneDistance(Double customNearPlaneDistance) {
		this.customNearPlaneDistance = customNearPlaneDistance;
	}

	/**
	 * AC addition to fix bug where stimuli aren't being presented. We should call this setup right before
	 * stimulus presentation.
	 */
	public void setup() {
		GL11.glMatrixMode(GL11.GL_PROJECTION);
		GL11.glLoadIdentity();

		double near = (customNearPlaneDistance != null) ? customNearPlaneDistance : PROJECTION_NEAR;
		double left = xmin * near / distance;
		double right = (xmax + hunit) * near / distance;
		double bottom = ymin * near / distance;
		double top = (ymax + vunit) * near / distance;
		GL11.glFrustum (left, right, bottom, top, near, distance + depth);

		GL11.glMatrixMode (GL11.GL_MODELVIEW);
		GL11.glLoadIdentity();
		GL11.glTranslated (0, 0, -distance);
	}

	/**
	 * AC: modified to call setup() right before draw. pushMatrix and popMatrix are added just in case.
	 */
	public void draw(Drawable scene, Context context) {
		context.setViewportIndex(0);
		context.setRenderer(this);
		setup();
		scene.draw(context);
	}
}