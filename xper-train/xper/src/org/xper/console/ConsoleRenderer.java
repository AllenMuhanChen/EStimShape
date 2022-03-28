package org.xper.console;

import org.xper.drawing.Context;
import org.xper.drawing.renderer.AbstractRenderer;

public interface ConsoleRenderer {

	void drawCanvas(Context context, String devId);

	AbstractRenderer getRenderer();

}