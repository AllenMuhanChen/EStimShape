package org.xper.drawing.drawables;

public interface Window {
	public int getWidth();
	public int getHeight();
	
	public void create ();
	public void swapBuffers();
	public void destroy();
}
