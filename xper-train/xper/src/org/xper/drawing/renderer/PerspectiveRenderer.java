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
	public PerspectiveRenderer() {
	}

	public void init() {
		super.init();
	}

	/**
	 * AC addition to fix bug where stimuli aren't being presented. We should call this setup right before
	 * stimulus presentation.
	 */
	public void setup() {
		GL11.glMatrixMode(GL11.GL_PROJECTION);
		GL11.glLoadIdentity();

		double left = xmin * PROJECTION_NEAR / distance;
		double right = (xmax + hunit) * PROJECTION_NEAR / distance;
		double bottom = ymin * PROJECTION_NEAR / distance;
		double top = (ymax + vunit) * PROJECTION_NEAR / distance;
		GL11.glFrustum (left, right, bottom, top, PROJECTION_NEAR, distance + depth);

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

	public PerspectiveRenderer(org.xper.alden.drawing.renderer.AbstractRenderer other) {
		this.width = other.getWidth();
		this.height = other.getHeight();
		this.depth = other.getDepth();
		this.distance = other.getDistance();
		this.pupilDistance = other.getPupilDistance();
		this.widthInPixel = other.widthInPixel;
		this.heightInPixel = other.heightInPixel;
		this.xmin = other.getXmin();
		this.xmax = other.getXmax();
		this.ymin = other.getYmin();
		this.ymax = other.getYmax();
		this.zmin = other.getZmin();
		this.zmax = other.getZmax();
		this.vpWidth = other.getVpWidth();
		this.vpHeight = other.getVpHeight();
		this.vpWidthmm = other.getVpWidthmm();
		this.vpHeightmm = other.getVpHeightmm();
		this.hunit = other.getHunit();
		this.vunit = other.getVunit();
	}

}