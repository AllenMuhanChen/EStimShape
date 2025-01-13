package org.xper.allen.drawing.png.preview;

import org.lwjgl.LWJGLException;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.DisplayMode;
import org.lwjgl.opengl.PixelFormat;
import org.xper.drawing.Window;

public class BaseWindow implements Window {
	PixelFormat pixelFormat = null;

	boolean paused = true;
	int width;
	int height;
	

	public BaseWindow() {
		super();
		DisplayMode mode = Display.getDisplayMode();
		this.width = mode.getWidth() / 2;
		this.height = mode.getHeight() / 2;
	}

	public BaseWindow(int height,int width) {
		super();
		this.width = width;
		this.height = height;
	}
	
	public void create() {
		try {
			Display.setDisplayMode(new DisplayMode(width,height));
			Display.setTitle("Lightweight Medial Axis Stimuli");
			Display.setVSyncEnabled(true);

			if (pixelFormat != null) {
				Display.create(pixelFormat);
			} else {
				Display.create();
			}
			
			Display.makeCurrent();
			
		} catch (LWJGLException e) {
		}
	}

	public void destroy() {
		Display.destroy();
	}

	public int getHeight() {
		return Display.getDisplayMode().getHeight();
	}

	public int getWidth() {
		return Display.getDisplayMode().getWidth();
	}
	
	public void setHeight(int h) {
		height = h;
	}

	public void setWidth(int w) {
		width = w;
	}
	
	public void swapBuffers() {
		Display.update();
	}

	public PixelFormat getPixelFormat() {
		return pixelFormat;
	}
	
	public void setPixelFormat(PixelFormat pixelFormat) {
		this.pixelFormat = pixelFormat;
	}
}
