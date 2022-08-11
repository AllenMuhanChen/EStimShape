package org.xper.sach.drawing;

import java.util.List;

import org.apache.log4j.Logger;
import org.lwjgl.LWJGLException;
import org.lwjgl.input.Keyboard;
import org.lwjgl.input.Mouse;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.DisplayMode;
import org.lwjgl.opengl.PixelFormat;
import org.xper.Dependency;
import org.xper.console.CommandListener;
import org.xper.console.MousePositionListener;
import org.xper.drawing.Window;
import org.xper.exception.XGLException;

public class TestingWindow implements Window {
	static Logger logger = Logger.getLogger(TestingWindow.class);

	@Dependency
	PixelFormat pixelFormat = null;
	@Dependency
	List<MousePositionListener> mousePositionListeners;
	@Dependency
	List<CommandListener> commandListeners;

	boolean paused = true;
	int width;
	int height;
	

	public TestingWindow() {
		super();
		DisplayMode mode = Display.getDisplayMode();
		this.width = mode.getWidth() / 2;
		this.height = mode.getHeight() / 2;
	}

	public TestingWindow(int height,int width) {
		super();
		this.width = width;
		this.height = height;
	}
	
	public void create() {
		try {
//			DisplayMode mode = Display.getDisplayMode();
//			Display.setDisplayMode(new DisplayMode(mode.getWidth() / 2, mode.getHeight() / 2));
			Display.setDisplayMode(new DisplayMode(width,height));
			Display.setTitle("Testing Window");
			Display.setVSyncEnabled(true);

			if (pixelFormat != null) {
				Display.create(pixelFormat);
			} else {
				Display.create();
			}
			
			//Display.setLocation(200, 100);
			Display.makeCurrent();
			
		} catch (LWJGLException e) {
			throw new XGLException(e);
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
		// must be done before create()
		height = h;
	}

	public void setWidth(int w) {
		// must be done before create()
		width = w;
	}
	
	public void swapBuffers() {
		Display.update();
		if (Display.isCloseRequested()) {
			if (commandListeners != null) {
				fireExperimentStop();
			}
		}
		handleMouse();
		handleKeyboard();
	}

	void fireExperimentStop() {
		for (CommandListener listener : commandListeners) {
			listener.experimentStop();
		}
	}

	void fireExperimentResume() {
		for (CommandListener listener : commandListeners) {
			listener.experimentResume();
		}
	}

	public void fireExperimentPause() {
		for (CommandListener listener : commandListeners) {
			listener.experimentPause();
		}
	}

	void handleKeyboard() {
		if (commandListeners != null) {
			while (Keyboard.next()) {
				if (Keyboard.getEventKeyState()) {
					if (Keyboard.getEventKey() == Keyboard.KEY_ESCAPE) {
						fireExperimentStop();	
					}
					if (Keyboard.getEventKey() == Keyboard.KEY_SPACE) {
						if (paused) {
							fireExperimentResume();
						} else {
							fireExperimentPause();
						}
						paused = !paused;	
					}
				}
			}
		}
	}
	
	void handleKeyboard2() {
		if (commandListeners != null) {
			while (Keyboard.next()) {
				if (Keyboard.getEventKeyState()) {
					if (Keyboard.getEventKey() == Keyboard.KEY_ESCAPE) {
						fireExperimentStop();	
					}
					if (Keyboard.getEventKey() == Keyboard.KEY_SPACE) {
						if (paused) {
							fireExperimentResume();
						} //else {
							//fireExperimentPause();
						//}
						//paused = !paused;	
					}
				}
			}
		}
	}

	void handleMouse() {
		if (mousePositionListeners != null) {
			int x = -1;
			int y = -1;
			while (Mouse.next()) {
				x = Mouse.getX();
				y = Mouse.getY();
			}
			if (x >= 0 && y >= 0) {
				for (MousePositionListener listener : mousePositionListeners) {
					listener.mousePosition(x, y);
				}
			}
		}
	}

	public PixelFormat getPixelFormat() {
		return pixelFormat;
	}

	public void setPixelFormat(PixelFormat pixelFormat) {
		this.pixelFormat = pixelFormat;
	}

	public List<MousePositionListener> getMousePositionListeners() {
		return mousePositionListeners;
	}

	public void setMousePositionListeners(
			List<MousePositionListener> mousePositionListeners) {
		this.mousePositionListeners = mousePositionListeners;
	}

	public List<CommandListener> getCommandListeners() {
		return commandListeners;
	}

	public void setCommandListeners(List<CommandListener> commandListeners) {
		this.commandListeners = commandListeners;
	}

	public boolean isPaused() {
		return paused;
	}

	public void setPaused(boolean paused) {
		this.paused = paused;
	}
}
