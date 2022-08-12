package org.xper.drawing.object;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;

public class Rectangle implements Drawable {
	@Dependency
	boolean solid = true;
	@Dependency
	double width;
	@Dependency
	double height;

	static final int STEPS = 4;

	ByteBuffer array = ByteBuffer.allocateDirect(STEPS * 3 * Float.SIZE / 8)
			.order(ByteOrder.nativeOrder());
	
	public Rectangle(double width, double height) {
		super();
		this.width = width;
		this.height = height;
		
		initArray();
	}

	/**
	 * @param context
	 *            ignored.
	 */
	public void draw(Context context) {
		GL11.glInterleavedArrays(GL11.GL_V3F, 0, array);
		if (solid) {
			GL11.glDrawArrays(GL11.GL_POLYGON, 0, STEPS);
		} else {
			GL11.glDrawArrays(GL11.GL_LINE_LOOP, 0, STEPS);
		}
	}

	void initArray() {
		// V3F
		array.putFloat((float) (-width / 2.0));
		array.putFloat((float) (-height / 2.0));
		array.putFloat(0.0f);

		// V3F
		array.putFloat((float) (width / 2.0));
		array.putFloat((float) (-height / 2.0));
		array.putFloat(0.0f);

		// V3F
		array.putFloat((float) (width / 2.0));
		array.putFloat((float) (height / 2.0));
		array.putFloat(0.0f);

		// V3F
		array.putFloat((float) (-width / 2.0));
		array.putFloat((float) (height / 2.0));
		array.putFloat(0.0f);

		array.flip();
	}

	public boolean isSolid() {
		return solid;
	}

	public void setSolid(boolean solid) {
		this.solid = solid;
	}

	public double getWidth() {
		return width;
	}

	public void setWidth(double width) {
		this.width = width;
		
		initArray();
	}

	public double getHeight() {
		return height;
	}

	public void setHeight(double height) {
		this.height = height;
		
		initArray();
	}

}
