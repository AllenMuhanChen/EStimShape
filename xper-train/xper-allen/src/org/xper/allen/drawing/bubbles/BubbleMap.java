package org.xper.allen.drawing.bubbles;

import java.io.IOException;
import java.util.Map;

public interface BubbleMap {
    Map<PixelLocation, Double> generateNoiseMap() throws IOException;
}