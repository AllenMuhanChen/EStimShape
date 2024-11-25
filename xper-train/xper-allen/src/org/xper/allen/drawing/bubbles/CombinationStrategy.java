package org.xper.allen.drawing.bubbles;

import java.util.Map;

public interface CombinationStrategy {
    public Map<PixelLocation, Double> combine(Map<PixelLocation, Double> noiseMap1, Map<PixelLocation, Double> noiseMap2);
}