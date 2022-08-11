package org.xper.sach.drawing.screenobj;

import java.util.ArrayList;
import java.util.List;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.object.Rectangle;


public class HoleyRectangleObject extends Rectangle{

	public double width = 30;
	public double height = 30;
	public double tx = 0;
	public double ty = 0;
	public double tz = 0;
	public float r = 0.0f;
	public float g = 0.0f;
	public float b = 0.0f;
	public float a = 0.5f;
	public boolean smooth = true;
	public boolean solid = true;
	
	public List<TransparentCircleObject> holes; 

	public HoleyRectangleObject(float r, float g, float b, double w, double h, double tx, double ty, double tz, List<TransparentCircleObject> holes) {
		super(w,h);
		width = w;
		height = h;
		this.r = r;
		this.g = g;
		this.b = b;
		this.tx = tx;
		this.ty = ty;
		this.tz = tz;
		this.holes = new ArrayList<TransparentCircleObject>(holes);;

	}
	
	public void drawRect(Context context) {		
		GL11.glPushAttrib(GL11.GL_COLOR_BUFFER_BIT);
		GL11.glColor4f(r, g, b, a);
		GL11.glPushMatrix();

		GL11.glEnable(GL11.GL_BLEND);
		GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
//		GL11.glBlendFunc(GL11.GL_ZERO, GL11.GL_SRC_ALPHA);
		
//		GL11.glEnable(GL11.GL_STENCIL_TEST);
//		GL11.glClear(GL11.GL_STENCIL_BUFFER_BIT);
//		
//		GL11.glStencilFunc(GL11.GL_GEQUAL, 1, 0xFF);
//		GL11.glStencilOp(GL11.GL_KEEP, GL11.GL_REPLACE, GL11.GL_REPLACE);
//		GL11.glStencilMask(0xFF);
//
//		GL11.glColorMask(false, false, false, false);
//		GL11.glDepthMask(false);
		
		GL11.glTranslated(tx, ty, tz);
		this.draw(context);
		
//		GL11.glEnable(GL11.GL_BLEND);
//		GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
		
//		GL11.glColorMask(false, false, false, true);
//		GL11.glDepthMask(false);
		
		for (TransparentCircleObject h : holes) {
			h.draw(context);
		}
		GL11.glDisable(GL11.GL_BLEND);

//		GL11.glDisable(GL11.GL_DEPTH_TEST);
//		GL11.glColorMask(true, true, true, true);
//		GL11.glDepthMask(true);
//		GL11.glDisable(GL11.GL_STENCIL_TEST);
		GL11.glPopMatrix();
		GL11.glPopAttrib();
	}
	
	public double getWidth() {
		return width;
	}

	public double getHeight() {
		return height;
	}

	public double getTx() {
		return tx;
	}

	public double getTy() {
		return ty;
	}

	public double getTz() {
		return tz;
	}

	public float getR() {
		return r;
	}

	public void setR(float r) {
		this.r = r;
	}

	public float getG() {
		return g;
	}

	public void setG(float g) {
		this.g = g;
	}

	public float getB() {
		return b;
	}

	public void setB(float b) {
		this.b = b;
	}

}
