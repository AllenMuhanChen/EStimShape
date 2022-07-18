package org.xper.allen.nafc.blockgen;

import org.junit.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.Assert.*;

public class TypeFrequencyTest {

    @Test
    public void splits_even_number_into_two() {
        TypeFrequency<String> typeFrequency = buildBlockParam(0.5, 0.5);


        List<String> trialList = typeFrequency.getTrialList(10);


        assertTrue(Collections.frequency(trialList, "foo")==5);
        assertTrue(Collections.frequency(trialList, "bar")==5);
    }

    @Test(expected = IllegalArgumentException.class)
    public void error_when_split_odd_into_two() {
        TypeFrequency<String> typeFrequency = buildBlockParam(0.5, 0.5);


        List<String> trialList = typeFrequency.getTrialList(11);
    }

    @Test
    public void splits_into_three() {
        List<String> types = Arrays.asList("foo","bar","gee");
        List<Double> frequencies = Arrays.asList(0.33, 0.33, 0.33);
        TypeFrequency<String> typeFrequency = new TypeFrequency<>(types, frequencies);


        List<String> trialList = typeFrequency.getTrialList(9);


        assertTrue(Collections.frequency(trialList, "foo")==3);
        assertTrue(Collections.frequency(trialList, "bar")==3);
        assertTrue(Collections.frequency(trialList, "gee")==3);
    }

    @Test
    public void accepts_0_as_frequency() {
        TypeFrequency<String> typeFrequency = buildBlockParam(1, 0);


        List<String> trialList = typeFrequency.getTrialList(10);


        assertTrue(Collections.frequency(trialList, "foo")==10);
        assertTrue(Collections.frequency(trialList, "bar")==0);
    }

    @Test(expected = IllegalArgumentException.class)
    public void error_when_frequencies_dont_add_to_1(){
        TypeFrequency<String> typeFrequency = buildBlockParam(0.5, 0.3);


        List<String> trialList = typeFrequency.getTrialList(10);
    }

    private TypeFrequency<String> buildBlockParam(double fooFrequency, double barFrequency) {
        List<String> types = Arrays.asList("foo","bar");
        List<Double> frequencies = Arrays.asList(fooFrequency, barFrequency);
        TypeFrequency<String> typeFrequency = new TypeFrequency<>(types, frequencies);
        return typeFrequency;
    }
}