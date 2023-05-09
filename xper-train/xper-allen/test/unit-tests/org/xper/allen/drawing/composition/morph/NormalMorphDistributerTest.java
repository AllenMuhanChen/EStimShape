package org.xper.allen.drawing.composition.morph;

import org.junit.Test;

import java.util.Arrays;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.*;

public class NormalMorphDistributerTest {

    @Test
    public void max_magnitude_leads_to_max() {
        NormalMorphDistributer normalMorphDistributer = new NormalMorphDistributer(1/3.0);
        List<AtomicReference<Double>> paramMagnitudes = Arrays.asList(
                new AtomicReference<>(0.0),
                new AtomicReference<>(0.0),
                new AtomicReference<>(0.0));

        normalMorphDistributer.distributeMagnitudeTo(paramMagnitudes, 1.0);
        System.out.println(paramMagnitudes);
        assertEquals(paramMagnitudes.stream().mapToDouble(AtomicReference::get).sum(), 3.0, 0.0001);
    }

    @Test
    public void test(){
        NormalMorphDistributer normalMorphDistributer = new NormalMorphDistributer(1/3.0);
        List<AtomicReference<Double>> paramMagnitudes = Arrays.asList(
                new AtomicReference<>(0.0),
                new AtomicReference<>(0.0),
                new AtomicReference<>(0.0));

        normalMorphDistributer.distributeMagnitudeTo(paramMagnitudes, 0.5);
        System.out.println(paramMagnitudes);
        assertEquals(paramMagnitudes.stream().mapToDouble(AtomicReference::get).sum(), 1.5, 0.0001);
    }
}