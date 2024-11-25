package org.xper.allen.drawing.bubbles;

import java.io.IOException;
import java.util.*;

public class CombinationBubbleMap implements BubbleMap {
    public List<BubbleMap> bubbleMaps;
    public CombinationStrategy strategy;

    public CombinationBubbleMap(List<BubbleMap> bubbleMaps, CombinationStrategy strategy) {
        this.bubbleMaps = bubbleMaps;
        this.strategy = strategy;
    }


    @Override
    public Map<PixelLocation, Double> generateNoiseMap() throws IOException {
        Map<PixelLocation, Double> noiseMap = new HashMap<>();
        for (BubbleMap bubbleMap : bubbleMaps) {
            Map<PixelLocation, Double> newMap = new HashMap<>();
            newMap.putAll(bubbleMap.generateNoiseMap());

            if (noiseMap.isEmpty()) {
                noiseMap.putAll(newMap);
            } else {
                noiseMap = strategy.combine(noiseMap, newMap);
            }
        }

        return noiseMap;
    }



    public CombinationStrategy getStrategy() {
        return strategy;
    }

    public void setStrategy(CombinationStrategy strategy) {
        this.strategy = strategy;
    }
}