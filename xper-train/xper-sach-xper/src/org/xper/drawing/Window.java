package org.xper.drawing;

public interface Window {
	public int getWidth();
	public int getHeight();
	
	public void create ();
	public void swapBuffers();
	public void destroy();
}
