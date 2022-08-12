package org.xper.rfplot;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.util.MathUtil;

public class RFPlotGaborObject implements RFPlotDrawable {
	static final int STEPS = 1024;
	
	GaborSpec spec;
	
	ByteBuffer array = ByteBuffer.allocateDirect(
			STEPS * (3 + 2 + 3) * 4 * Float.SIZE / 8).order(
			ByteOrder.nativeOrder());
		
	static ByteBuffer makeTexture(int w, int h) {
		ByteBuffer texture = ByteBuffer.allocateDirect(
				w * w * Float.SIZE / 8).order(
				ByteOrder.nativeOrder());
		
		double dist;
		int i, j;

		double std = 0.3f;
		double norm_max = MathUtil.normal(0, 0, std);

		for (i = 0; i < w; i++) {
			double x = (double) i / (w - 1) * 2 - 1;
			for (j = 0; j < h; j++) {
				double y = (double) j / (h - 1) * 2 - 1;
				dist = Math.sqrt(x * x + y * y);
				float n = (float) (MathUtil.normal(dist, 0, std) / norm_max);
				texture.putFloat(n);
			}
		}
		texture.flip();
		
		return texture;
	}

	public void draw(Context context) {
		double rfRadius = 1;

		spec.setPhase(spec.getPhase() + Math.PI * 4.0 / 100);

		double xCenter = spec.getXCenter() * rfRadius;
		double yCenter = spec.getYCenter() * rfRadius;
		double orientation = spec.getOrientation();
		double frequency = spec.getFrequency();
		double phase = spec.getPhase();
		double size = spec.getSize() * rfRadius;

		float cury;
		float color_ratio;
		float texy;
		float next_y, next_texy;

		for (int i = 0; i < STEPS; i++) {
			cury = (float) (2.0 * size * i / STEPS - size);
			next_y = (float) (2.0 * size * (i + 1) / STEPS - size);
			color_ratio = (float) ((Math.sin(2.0 * Math.PI * cury * frequency
					+ phase) + 1.0) / 2.0);
			texy = (float) ((cury + size) / size / 2.0);
			next_texy = (float) ((next_y + size) / size / 2.0);

			// T2F
			array.putFloat(0.0f);
			array.putFloat(texy);
			// C3F
			array.putFloat(color_ratio);
			array.putFloat(color_ratio);
			array.putFloat(color_ratio);
			// V3F
			array.putFloat((float) -size);
			array.putFloat(cury);
			array.putFloat(0.0f);

			// T2F
			array.putFloat(1.0f);
			array.putFloat(texy);
			// C3F
			array.putFloat(color_ratio);
			array.putFloat(color_ratio);
			array.putFloat(color_ratio);
			// V3F
			array.putFloat((float) size);
			array.putFloat(cury);
			array.putFloat(0.0f);

			// T2F
			array.putFloat(1.0f);
			array.putFloat(next_texy);
			// C3F
			array.putFloat(color_ratio);
			array.putFloat(color_ratio);
			array.putFloat(color_ratio);
			// V3F
			array.putFloat((float) size);
			array.putFloat(next_y);
			array.putFloat(0.0f);

			// T2F
			array.putFloat(0.0f);
			array.putFloat(next_texy);
			// C3F
			array.putFloat(color_ratio);
			array.putFloat(color_ratio);
			array.putFloat(color_ratio);
			// V3F
			array.putFloat((float) -size);
			array.putFloat(next_y);
			array.putFloat(0.0f);
		}

		array.flip();
		GL11.glInterleavedArrays(GL11.GL_T2F_C3F_V3F, 0, array);

		GL11.glEnable(GL11.GL_TEXTURE_2D);

		GL11.glTranslated(xCenter, yCenter, 0);
		GL11.glRotatef((float) (orientation * 180 / Math.PI), 0.0f, 0.0f, 1.0f);

		GL11.glDrawArrays(GL11.GL_QUADS, 0, STEPS * 4);

		GL11.glDisable(GL11.GL_TEXTURE_2D);
		GL11.glRotatef((float) (-orientation * 180 / Math.PI), 0.0f, 0.0f,
						1.0f);
		GL11.glTranslatef((float) -xCenter, (float) -yCenter, 0f);
	}

	public static void initGL() {
		int w = 1024;
		int h = 1024;
		ByteBuffer texture = makeTexture(w, h);

		GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 1);
		GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_ALPHA, w,
				h, 0, GL11.GL_ALPHA, GL11.GL_FLOAT, texture);
		GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S,
				GL11.GL_CLAMP);
		GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T,
				GL11.GL_CLAMP);
		GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER,
				GL11.GL_NEAREST);
		GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER,
				GL11.GL_NEAREST);
		GL11.glTexEnvf(GL11.GL_TEXTURE_ENV, GL11.GL_TEXTURE_ENV_MODE,
				GL11.GL_MODULATE);
		GL11.glEnable(GL11.GL_BLEND);
		GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
		GL11.glShadeModel(GL11.GL_SMOOTH);
	}

	public void setSpec(String s) {
		spec = GaborSpec.fromXml(s);
	}

}
