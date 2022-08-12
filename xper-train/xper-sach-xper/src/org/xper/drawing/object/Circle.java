package org.xper.drawing.object;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;

public class Circle implements Drawable {
	
	@Dependency
	boolean solid = false;
	@Dependency
	double radius;
	
	static final int STEPS = 200;
	ByteBuffer array = ByteBuffer.allocateDirect(
			STEPS * 3 * Float.SIZE / 8).order(
			ByteOrder.nativeOrder());

	/**
	 * @param context ignored.
	 */
	public void draw(Context context) {
		GL11.glInterleavedArrays(GL11.GL_V3F, 0, array);
		if (solid) {
			GL11.glDrawArrays(GL11.GL_POLYGON, 0, STEPS);
		} else {
			GL11.glDrawArrays(GL11.GL_LINE_LOOP, 0, STEPS);
		}
	}

	public double getRadius() {
		return radius;
	}
	
	void initArray() {
		for (int i = 0; i < STEPS; i ++) {
			double angle = i * 2 * Math.PI / STEPS;
			//V3F
			array.putFloat((float)(radius*Math.cos(angle)));
			array.putFloat((float)(radius*Math.sin(angle)));
			array.putFloat(0.0f);
		}
		array.flip();
	}

	public void setRadius(double radius) {
		this.radius = radius;
		
		initArray();
	}

	public boolean isSolid() {
		return solid;
	}

	public void setSolid(boolean solid) {
		this.solid = solid;
	}
}
