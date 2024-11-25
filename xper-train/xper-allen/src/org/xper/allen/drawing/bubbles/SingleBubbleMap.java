package org.xper.allen.drawing.bubbles;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class SingleBubbleMap implements BubbleMap{
    public List<Bubble> bubbles;
    public CombinationStrategy strategy;

    public SingleBubbleMap(List<Bubble> bubbles) {
        this.bubbles = bubbles;
        this.strategy = new AddCombinationStrategy();
    }


    @Override
    public Map<PixelLocation, Double> generateNoiseMap() throws IOException {
        Map<PixelLocation, Double> noiseMap = new HashMap<>();
        for (Bubble bubble : bubbles) {
            Map<PixelLocation, Double> newMap = new HashMap<>();
            newMap.putAll(bubble.getNoiseMap());

            if (noiseMap.isEmpty()) {
                noiseMap.putAll(newMap);
            } else {
                noiseMap = strategy.combine(noiseMap, newMap);
            }
        }

        return noiseMap;
    }

    public List<Bubble> getBubbles() {
        return bubbles;
    }

    public void setBubbles(List<Bubble> bubbles) {
        this.bubbles = bubbles;
    }

    public CombinationStrategy getStrategy() {
        return strategy;
    }

    public void setStrategy(CombinationStrategy strategy) {
        this.strategy = strategy;
    }
}