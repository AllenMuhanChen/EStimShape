package org.xper.drawing.renderer;

import org.xper.drawing.Context;
import org.xper.drawing.Drawable;

public interface Renderer {
	public void init(int w, int h);
	
	public void draw (Drawable scene, Context context);
}
