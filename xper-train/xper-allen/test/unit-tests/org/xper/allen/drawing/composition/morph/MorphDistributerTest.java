package org.xper.allen.drawing.composition.morph;

import org.junit.Test;

import java.util.Arrays;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.*;

public class MorphDistributerTest {

    @Test
    public void max_magnitude_leads_to_max() {
        MorphDistributer morphDistributer = new MorphDistributer();
        List<AtomicReference<Double>> paramMagnitudes = Arrays.asList(
                new AtomicReference<>(0.0),
                new AtomicReference<>(0.0),
                new AtomicReference<>(0.0));

        morphDistributer.distributeMagnitudeTo(paramMagnitudes, 1.0);
        System.out.println(paramMagnitudes);
        assertEquals(paramMagnitudes.stream().mapToDouble(AtomicReference::get).sum(), 3.0, 0.0001);
    }

    @Test
    public void test(){
        MorphDistributer morphDistributer = new MorphDistributer();
        List<AtomicReference<Double>> paramMagnitudes = Arrays.asList(
                new AtomicReference<>(0.0),
                new AtomicReference<>(0.0),
                new AtomicReference<>(0.0));

        morphDistributer.distributeMagnitudeTo(paramMagnitudes, 0.5);
        System.out.println(paramMagnitudes);
        assertEquals(paramMagnitudes.stream().mapToDouble(AtomicReference::get).sum(), 1.5, 0.0001);
    }
}