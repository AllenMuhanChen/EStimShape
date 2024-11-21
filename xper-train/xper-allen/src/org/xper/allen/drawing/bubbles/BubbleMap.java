package org.xper.allen.drawing.bubbles;

import java.io.IOException;
import java.util.*;

public class BubbleMap {
    public List<Bubble> bubbles;
    public CombinationStrategy strategy;

    public BubbleMap(List<Bubble> bubbles, CombinationStrategy strategy) {
        this.bubbles = bubbles;
        this.strategy = strategy;
    }

    public Map<PixelLocation, Double> generateNoiseMap() throws IOException {
        Map<PixelLocation, Double> noiseMap = new HashMap<>();
        for (Bubble bubble : bubbles) {
            bubble.generateBubblePixels();
            List<NoisyPixel> noisyPixels = bubble.getNoisyPixels();
            if (noiseMap.isEmpty()){
                for (NoisyPixel noisyPixel : noisyPixels){
                    noiseMap.put(noisyPixel.getPixelLocation(), noisyPixel.getNoiseChance());
                }
            }
            for (NoisyPixel newPixel : noisyPixels) {
                //If Matching, add the noise chance to the existing noise chance
                double newNoiseChance = newPixel.getNoiseChance();
                if (noiseMap.containsKey(newPixel.getPixelLocation())) {
                    Double oldNoiseChance = noiseMap.get(newPixel.getPixelLocation());
                    if (strategy == CombinationStrategy.ADD) {
                        double combinedNoiseChance = oldNoiseChance + newNoiseChance;
                        combinedNoiseChance = Math.min(combinedNoiseChance, 1.0);
                        noiseMap.put(newPixel.getPixelLocation(), combinedNoiseChance);
                    }
                    //If AND, take geometric mean
                    else if (strategy == CombinationStrategy.AND) {
                        boolean isAnd = oldNoiseChance > 0.1 && newNoiseChance > 0.1;
                        double combinedNoiseChance = isAnd ? 1.0 : 0.0;
                        System.out.println("Old Noise Chance: " + oldNoiseChance + " New Noise Chance: " + newNoiseChance + " Combined Noise Chance: " + combinedNoiseChance);
                        noiseMap.put(newPixel.getPixelLocation(), combinedNoiseChance);
                    }
                    else{
                        throw new IllegalArgumentException("Invalid CombinationStrategy");
                    }
                } else {
                    if (strategy == CombinationStrategy.AND) {
                        newNoiseChance = 0;
                    }
                    noiseMap.put(newPixel.getPixelLocation(), newNoiseChance);
                }
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