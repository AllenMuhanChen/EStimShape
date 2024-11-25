package org.xper.allen.drawing.bubbles;

import java.util.HashMap;
import java.util.Map;

public class AndCombinationStrategy implements CombinationStrategy{

    @Override
    public Map<PixelLocation, Double> combine(Map<PixelLocation, Double> noiseMap1, Map<PixelLocation, Double> noiseMap2) {
        Map<PixelLocation, Double> combinedMap = new HashMap<>();
        for (Map.Entry<PixelLocation, Double> NoisyPixel2 : noiseMap2.entrySet()) {
            PixelLocation pixelLocation2 = NoisyPixel2.getKey();
            Double noiseChance2 = NoisyPixel2.getValue();
            if (noiseMap1.containsKey(pixelLocation2)) {
                Double noiseChance1 = noiseMap1.get(pixelLocation2);
                boolean isAnd = noiseChance1 > 0.1 && noiseChance2 > 0.1;
                double combinedNoiseChance = isAnd ? 1 : 0;
                combinedMap.put(pixelLocation2, combinedNoiseChance);
            }
        }
        return combinedMap;
    }
}