package org.xper.allen.ga;

import org.junit.Test;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

public class StandardSpikeRateAnalyzerTest {

    /**
     * 6 from top 10%
     * 4 from next 20%
     * 3 from next 20%
     * 2 from next 20%
     * 1 from botton 10%
     */
    @Test
    public void chooses_16_out_of_20() {
        StandardParentSelectorStrategy analyzer = new StandardParentSelectorStrategy();


        List<Double> spikeRates = new LinkedList<>();
        List<Long> stimIds = new LinkedList<>();
        for (int i=1; i<=20; i++){
            stimIds.add((long) i);
        }
        for(int i=20; i>=1; i--){
            spikeRates.add((double) i);
        }

        List<Long> chosenParents = analyzer.analyze(Parent.createParentListFrom(stimIds, spikeRates));
        Map<Long, Integer> frequencies = countFrequencies(chosenParents);
        System.out.println(chosenParents);
        assertTrue(frequencies.getOrDefault(1L,0) + frequencies.getOrDefault(2L,0) == 6);
        assertTrue(frequencies.getOrDefault(3L, 0) + frequencies.getOrDefault(4L, 0) + frequencies.getOrDefault(5L,0) + frequencies.getOrDefault(6L, 0) == 4);
        assertTrue(frequencies.getOrDefault(7L, 0) + frequencies.getOrDefault(8L, 0) + frequencies.getOrDefault(9L,0) + frequencies.getOrDefault(10L, 0) == 3);
        assertTrue(frequencies.getOrDefault(11L, 0) + frequencies.getOrDefault(12L, 0) + frequencies.getOrDefault(13L,0) + frequencies.getOrDefault(14L, 0) == 2);
        assertTrue(frequencies.getOrDefault(19L, 0) + frequencies.getOrDefault(20L, 0) == 1);

    }

    public static Map<Long, Integer> countFrequencies(List<Long> list)
    {
        // hashmap to store the frequency of element
        Map<Long, Integer> hm = new HashMap<Long, Integer>();

        for (Long i : list) {
            Integer j = hm.get(i);
            hm.put(i, (j == null) ? 1 : j + 1);
        }

        return hm;
    }
}