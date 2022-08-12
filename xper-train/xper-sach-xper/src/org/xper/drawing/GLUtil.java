package org.xper.drawing;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.Rectangle;
import org.xper.drawing.object.Square;

public class GLUtil {
	public static void drawCircle (Circle circle, double size, boolean solid, double tx, double ty, double tz) {
		GL11.glPushMatrix();
		GL11.glTranslated(tx, ty, tz);
		circle.setRadius(size);
		circle.setSolid(solid);
		circle.draw(null);
		GL11.glPopMatrix();
	}
	
	public static void drawSquare (Square square, double size, boolean solid, double tx, double ty, double tz) {
		square.setSize(size);
		square.setSolid(solid);
		GL11.glPushMatrix();
		GL11.glTranslated(tx, ty, tz);
		square.draw(null);
		GL11.glPopMatrix();
	}
	
	public static void drawRectangle(Rectangle rect, double tx, double ty, double tz, float r, float g, float b) {
		GL11.glPushAttrib(GL11.GL_COLOR_BUFFER_BIT);
		GL11.glColor3f(r, g, b);
		GL11.glPushMatrix();
		GL11.glTranslated(tx, ty, tz);
		rect.draw(null);
		GL11.glPopMatrix();
		GL11.glPopAttrib();
	}
}
