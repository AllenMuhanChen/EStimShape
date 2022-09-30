package org.xper.drawing;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.Rectangle;
import org.xper.drawing.object.Square;

public class GLUtil {
	static RGBColor defaultColor = new RGBColor(1, 1, 0);
	public static void drawCircle (Circle circle, double size, boolean solid, double tx, double ty, double tz) {
		GL11.glPushMatrix();
		GL11.glColor3f(defaultColor.red, defaultColor.green, defaultColor.blue);
		GL11.glTranslated(tx, ty, tz);
		circle.setRadius(size);
		circle.setSolid(solid);
		circle.draw(null);
		GL11.glPopMatrix();
	}

	public static void drawCircle (Circle circle, double tx, double ty, double tz, float r, float g, float b) {
		GL11.glPushMatrix();
		GL11.glColor3f(r, g, b);
		GL11.glTranslated(tx, ty, tz);
		circle.draw(null);
		GL11.glPopMatrix();
		GL11.glClear(GL11.GL_COLOR);
	}


	public static void drawSquare (Square square, double size, boolean solid, double tx, double ty, double tz) {
		GL11.glPopAttrib();
		square.setSize(size);
		square.setSolid(solid);
		GL11.glPushMatrix();
		GL11.glColor3f(defaultColor.red, defaultColor.green, defaultColor.blue);
		GL11.glTranslated(tx, ty, tz);
		square.draw(null);
		GL11.glPopMatrix();
	}

	public static void drawSquare (Square square, double tx, double ty, double tz, float r, float g, float b) {
		GL11.glPushMatrix();
//		GL11.glPushAttrib(GL11.GL_COLOR);
		GL11.glPushMatrix();
		GL11.glTranslated(tx, ty, tz);
		GL11.glColor3f(r, g, b);
		square.draw(null);
//		GL11.glPopAttrib();
		GL11.glPopMatrix();
		GL11.glClear(GL11.GL_COLOR);
	}
	
	public static void drawRectangle(Rectangle rect, double tx, double ty, double tz, float r, float g, float b) {
		GL11.glPushMatrix();
		GL11.glColor3f(r, g, b);
		GL11.glTranslated(tx, ty, tz);
		rect.draw(null);
		GL11.glPopMatrix();
	}
}
