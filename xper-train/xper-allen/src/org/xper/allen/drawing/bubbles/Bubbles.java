package org.xper.allen.drawing.bubbles;

import java.util.List;

public interface Bubbles {
    List<NoisyPixel> generateBubbles(String imagePath, int nBubbles, double bubbleSigma);
}