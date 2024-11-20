package org.xper.allen.drawing.bubbles;

import java.util.List;

public interface BubbleFactory {
    List<Bubble> generateBubbles(String imagePath, int nBubbles, double bubbleSigma);
}