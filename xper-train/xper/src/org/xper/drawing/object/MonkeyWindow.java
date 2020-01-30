package org.xper.drawing.object;

import org.lwjgl.LWJGLException;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.DisplayMode;
import org.lwjgl.opengl.PixelFormat;
import org.xper.Dependency;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Window;
import org.xper.exception.XGLException;

public class MonkeyWindow implements Window {
	/**
	 * fullscreen should be set to true for actual experiments.
	 */
	@Dependency
	boolean fullscreen = true;
	@Dependency
	PixelFormat pixelFormat = null; // new PixelFormat(0, 8, 1, 4);

	@Dependency
	double canvasScaleFactor = DEFAULT_CANVAS_SCALE_FACTOR;

	int screenWidth;
	int screenHeight;

	static final double DEFAULT_CANVAS_SCALE_FACTOR = 2;

	public MonkeyWindow() {
		DisplayMode mode = Display.getDisplayMode();
		screenWidth = mode.getWidth();
		screenHeight = mode.getHeight();
	}
	public void create() {
		try {
			System.setProperty("org.lwjgl.opengl.Display.noinput", "true");
			//System.setProperty("LWJGL_DISABLE_NETWM", "true");

			if (fullscreen) {
				Display.setFullscreen(true);
			} else {
				// for testing, use half screen width and half screen height as
				// width and height of monkey window
				int height = (int)(screenHeight / canvasScaleFactor);
				int width = height * 8 / 3;
				Display.setDisplayMode(new DisplayMode(width,height));
				Display.setTitle("Monkey Monitor");
			}
			if (pixelFormat != null) {
				Display.create(pixelFormat);
			} else {
				Display.create();
			}

			Display.setVSyncEnabled(true);

		} catch (Exception e) {
			throw new XGLException(e);
		}
	}

	public int getWidth() {
		return Display.getDisplayMode().getWidth();
	}

	public int getHeight() {
		return Display.getDisplayMode().getHeight();
	}

	public int getScreenHeight() {
		return screenHeight;
	}

	public int getScreenWidth() {
		return screenWidth;
	}

	public Coordinates2D getScreenDimension() {
		return new Coordinates2D(getScreenWidth(), getScreenHeight());
	}

	public void destroy() {
		Display.destroy();
	}

	public void swapBuffers() {
		// Do not handle events. Or fullscreen will unexpectedly get minimized.
		if (fullscreen) {
			try {
				Display.swapBuffers();
			} catch (LWJGLException e) {
				throw new XGLException(e);
			}
		} else {
			Display.update();
		}
	}

	public boolean isFullscreen() {
		return fullscreen;
	}

	public void setFullscreen(boolean fullscreen) {
		this.fullscreen = fullscreen;
	}

	public PixelFormat getPixelFormat() {
		return pixelFormat;
	}

	public void setPixelFormat(PixelFormat pixelFormat) {
		this.pixelFormat = pixelFormat;
	}
	public double getCanvasScaleFactor() {
		return canvasScaleFactor;
	}
	public void setCanvasScaleFactor(double canvasScaleFactor) {
		this.canvasScaleFactor = canvasScaleFactor;
	}

}
