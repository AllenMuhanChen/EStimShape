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
//		GL11.glClear(GL11.GL_COLOR);
	}


	public static void drawSquare (Square square, double size, boolean solid, double tx, double ty, double tz) {
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
		GL11.glTranslated(tx, ty, tz);
		GL11.glColor3f(r, g, b);
		square.draw(null);
		GL11.glPopMatrix();
//		GL11.glClear(GL11.GL_COLOR);
	}

	public static void drawRectangle(Rectangle rect, double tx, double ty, double tz, float r, float g, float b) {
		GL11.glPushMatrix();
		GL11.glColor3f(r, g, b);
		GL11.glTranslated(tx, ty, tz);
		rect.draw(null);
		GL11.glPopMatrix();
	}

	public static void drawLine(double x1, double y1, double x2, double y2, float r, float g, float b) {
		GL11.glPushMatrix();
		GL11.glColor3f(r, g, b); // Set the color for the line
		GL11.glBegin(GL11.GL_LINES); // Begin drawing lines
		GL11.glVertex2d(x1, y1); // Specify the start point of the line
		GL11.glVertex2d(x2, y2); // Specify the end point of the line
		GL11.glEnd(); // End drawing lines
		GL11.glPopMatrix();
	}
}