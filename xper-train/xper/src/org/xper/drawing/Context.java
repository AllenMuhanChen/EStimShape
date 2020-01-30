package org.xper.drawing;

import org.xper.drawing.renderer.AbstractRenderer;

public class Context {
	int viewportIndex;
	AbstractRenderer renderer;
	
	public AbstractRenderer getRenderer() {
		return renderer;
	}
	public void setRenderer(AbstractRenderer renderer) {
		this.renderer = renderer;
	}
	public int getViewportIndex() {
		return viewportIndex;
	}
	public void setViewportIndex(int viewportIndex) {
		this.viewportIndex = viewportIndex;
	}
}
