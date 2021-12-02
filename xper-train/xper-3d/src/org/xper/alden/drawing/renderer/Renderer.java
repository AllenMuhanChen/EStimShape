package org.xper.alden.drawing.renderer;

import org.xper.alden.drawing.drawables.Drawable;

public interface Renderer {
	public void init(int w, int h);
	public void draw (Drawable scene);
}
