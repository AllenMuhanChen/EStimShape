package org.xper.allen.drawing.composition.morph;

import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;

import java.util.ArrayList;
import java.util.List;

public class ComponentMorphParametersTest {

    private ComponentMorphParameters morphParams;

    @Before
    public void setUp() throws Exception {
        morphParams = new ComponentMorphParameters(1.0);
    }

    @Test
    public void test_magnitude_distribution() {
        morphParams = new ComponentMorphParameters(0.5);
        List<Double> magnitudes = new ArrayList<>();
        magnitudes.add(morphParams.orientationMagnitude);
        magnitudes.add(morphParams.rotationMagnitude);
        magnitudes.add(morphParams.lengthMagnitude);
        magnitudes.add(morphParams.curvatureMagnitude);
        magnitudes.add(morphParams.radiusProfileMagnitude);

        double sum = 0.0;
        for (Double magnitude : magnitudes) {
            sum += magnitude;
            Assert.assertTrue(magnitude >= 0.0);
            Assert.assertTrue(magnitude <= 1.0);
        }
        Assert.assertTrue(sum <= 2.5);
    }
}