package org.xper.sach;


import org.lwjgl.opengl.GL11;
import org.xper.drawing.AbstractTaskScene;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;

public abstract class AbstractSachTaskScene extends AbstractTaskScene implements SachTaskScene {
	
	public void drawTargetScene(Context context) {
		blankScreen.draw(null);
		renderer.draw(new Drawable() {
			public void draw(Context context) {
				if (useStencil) {
					// 0 will pass for stimulus region
					GL11.glStencilFunc(GL11.GL_EQUAL, 0, 1);
				}
				drawTargetObjects(context);
				if (useStencil) {
					// 1 will pass for fixation and marker regions
					GL11.glStencilFunc(GL11.GL_EQUAL, 1, 1);
				}
				getFixation().draw(context);
				marker.draw(context);
			}
		}, context);
	}
	
	abstract protected void drawTargetObjects (Context context);
}
