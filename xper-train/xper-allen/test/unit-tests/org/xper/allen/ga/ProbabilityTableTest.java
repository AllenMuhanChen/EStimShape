package org.xper.allen.ga;

import org.junit.Test;

import java.util.Arrays;

import static org.junit.Assert.*;

public class ProbabilityTableTest {

    @Test
    public void testSampleWithReplacement() {
        String[] items = {"a", "b", "c"};
        Double[] probabilities = {0.1, 0.2, 0.7};
        ProbabilityTable<String> table = new ProbabilityTable<>(Arrays.asList(items), Arrays.<Double>asList(probabilities));
        int[] counts = new int[3];
        for (int i = 0; i < 10000; i++) {
            String item = table.sampleWithReplacement();
            if (item.equals("a")) {
                counts[0]++;
            } else if (item.equals("b")) {
                counts[1]++;
            } else if (item.equals("c")) {
                counts[2]++;
            }
        }
        assertEquals(1000, counts[0], 100);
        assertEquals(2000, counts[1], 100);
        assertEquals(7000, counts[2], 100);
    }



}