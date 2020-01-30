package org.xper.drawing.object;

import org.xper.drawing.Context;

public class LeftRightOverlapScreenMarker extends AlternatingScreenMarker {
	public void draw(Context context) {
		if (context.getViewportIndex() == viewportIndex) {
			drawMarker(context, whiteColor, blackColor);
		} else {
			drawMarker(context, blackColor, blackColor);
		}
	}
	public void drawAllOff(Context context) {
		drawMarker(context, blackColor, blackColor);
	}
}
