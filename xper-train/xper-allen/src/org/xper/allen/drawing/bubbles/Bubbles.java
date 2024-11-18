package org.xper.allen.drawing.bubbles;

import java.util.List;

public interface Bubbles {
    List<BubblePixel> generateBubbles(String imagePath, int nBubbles, double bubbleSigma);
}