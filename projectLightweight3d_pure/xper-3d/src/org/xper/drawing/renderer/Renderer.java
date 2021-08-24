package org.xper.drawing.renderer;

import org.xper.drawing.drawables.Drawable;

public interface Renderer {
	public void init(int w, int h);
	public void draw (Drawable scene);
}
