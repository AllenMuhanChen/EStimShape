package org.xper.allen.drawing.bubbles;

import java.util.HashMap;
import java.util.Map;

public class AddCombinationStrategy implements CombinationStrategy{

    @Override
    public Map<PixelLocation, Double> combine(Map<PixelLocation, Double> noiseMap1, Map<PixelLocation, Double> noiseMap2) {
        Map<PixelLocation, Double> combinedMap = new HashMap<>(noiseMap1);
        for (Map.Entry<PixelLocation, Double> noisyPixel2 : noiseMap2.entrySet()) {
            PixelLocation pixelLocation2 = noisyPixel2.getKey();
            Double noiseChance2 = noisyPixel2.getValue();
            if (noiseMap1.containsKey(pixelLocation2)) {
                Double noiseChance1 = noiseMap1.get(pixelLocation2);
                double combinedNoiseChance = Math.min(noiseChance1 + noiseChance2, 1);
                combinedMap.put(pixelLocation2, combinedNoiseChance);
            } else {
                combinedMap.put(pixelLocation2, noiseChance2);
            }
        }
        return combinedMap;
    }
}