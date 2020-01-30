package org.xper.rds;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.concurrent.atomic.AtomicReference;

import org.lwjgl.opengl.GL11;
import org.xper.Dependency;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.drawing.RGBColor;
import org.xper.util.MathUtil;

public class RdsSquare implements Drawable {
	
	static class ArrayData {
		public ByteBuffer rectArray;
		public int rectArraySize;
		
		public ByteBuffer dotArray;
		public int dotArraySize;
	}

	@Dependency
	float dotSize = 1;
	@Dependency
	float dotDensity = 0.3f;
	@Dependency
	RGBColor dotColor = new RGBColor(0, 0, 0);
	@Dependency
	float size;
	
	AtomicReference<ArrayData> data = new AtomicReference<ArrayData>();
	
	void pushDot (ByteBuffer dotArray, float x, float y) {
		// V3F
		dotArray.putFloat(x + (-dotSize / 2.0f));
		dotArray.putFloat(y + (-dotSize / 2.0f));
		dotArray.putFloat(0.0f);

		// V3F
		dotArray.putFloat(x + (dotSize / 2.0f));
		dotArray.putFloat(y + (-dotSize / 2.0f));
		dotArray.putFloat(0.0f);

		// V3F
		dotArray.putFloat(x + (dotSize / 2.0f));
		dotArray.putFloat(y + (dotSize / 2.0f));
		dotArray.putFloat(0.0f);

		// V3F
		dotArray.putFloat(x + (-dotSize / 2.0f));
		dotArray.putFloat(y + (dotSize / 2.0f));
		dotArray.putFloat(0.0f);
	}
	
	void init () {
		ArrayData d = new ArrayData();
		
		float area = size * size;
		float dotArea = dotSize * dotSize;
		int nDots = Math.round(dotDensity * area /dotArea + 0.5f);
		d.dotArraySize = nDots * 4;
		d.dotArray = ByteBuffer.allocateDirect(d.dotArraySize * 3 * Float.SIZE / 8).order(ByteOrder.nativeOrder());
		
		float range = (size - dotSize) / 2.0f;
		for (int i = 0; i < nDots; i ++) {
			float x = (float)MathUtil.rand(-range, range);
			float y = (float)MathUtil.rand(-range, range);
			pushDot (d.dotArray, x, y);
		}
		
		d.dotArray.flip();
		
		d.rectArraySize = 4;
		d.rectArray = ByteBuffer.allocateDirect(d.rectArraySize * 3 * Float.SIZE / 8).order(ByteOrder.nativeOrder());
		// V3F
		d.rectArray.putFloat(-size / 2.0f);
		d.rectArray.putFloat(-size / 2.0f);
		d.rectArray.putFloat(0.0f);

		// V3F
		d.rectArray.putFloat(size / 2.0f);
		d.rectArray.putFloat(-size / 2.0f);
		d.rectArray.putFloat(0.0f);

		// V3F
		d.rectArray.putFloat(size / 2.0f);
		d.rectArray.putFloat(size / 2.0f);
		d.rectArray.putFloat(0.0f);

		// V3F
		d.rectArray.putFloat(-size / 2.0f);
		d.rectArray.putFloat(size / 2.0f);
		d.rectArray.putFloat(0.0f);
		
		d.rectArray.flip();
		
		data.set(d);
	}
	
	@Override
	public void draw(Context context) {
		ArrayData d = data.get();
		
		GL11.glInterleavedArrays(GL11.GL_V3F, 0, d.rectArray);
		GL11.glDrawArrays(GL11.GL_QUADS, 0, d.rectArraySize);
		GL11.glColor3f(dotColor.getRed(), dotColor.getGreen(), dotColor.getBlue());
		GL11.glInterleavedArrays(GL11.GL_V3F, 0, d.dotArray);
		GL11.glDrawArrays(GL11.GL_QUADS, 0, d.dotArraySize);
	}

	public float getDotSize() {
		return dotSize;
	}

	public void setDotSize(float dotSize) {
		this.dotSize = dotSize;
	}

	public float getDotDensity() {
		return dotDensity;
	}

	public void setDotDensity(float dotDensity) {
		this.dotDensity = dotDensity;
	}

	public RGBColor getDotColor() {
		return dotColor;
	}

	public void setDotColor(RGBColor dotColor) {
		this.dotColor = dotColor;
	}

	public float getSize() {
		return size;
	}

	public void setSize(float size) {
		this.size = size;
	}

}
