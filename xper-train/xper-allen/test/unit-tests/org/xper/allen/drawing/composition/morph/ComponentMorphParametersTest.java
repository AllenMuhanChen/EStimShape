package org.xper.allen.drawing.composition.morph;

import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

public class ComponentMorphParametersTest {

    private ComponentMorphParameters morphParams;

    @Before
    public void setUp() throws Exception {
//        morphParams = new ComponentMorphParameters(1.0, new NormalMorphDistributer(1/3.0));
    }

    @Test
    public void test_magnitude_distribution() {
        morphParams = new ComponentMorphParameters(0.5, new NormalMorphDistributer(1/3.0));
        List<Double> magnitudes = new ArrayList<>();
        magnitudes.add(morphParams.orientationMagnitude);
        magnitudes.add(morphParams.rotationMagnitude);
        magnitudes.add(morphParams.lengthMagnitude);
        magnitudes.add(morphParams.curvatureMagnitude);
        magnitudes.add(morphParams.radiusProfileMagnitude);

        double sum = 0.0;
        // Assert that each magnitude is between 0 and 1
        for (Double magnitude : magnitudes) {
            sum += magnitude;
            Assert.assertTrue(magnitude >= 0.0);
            Assert.assertTrue(magnitude <= 1.0);
        }
        // Assert that the sum of the magnitudes is less than or equal to 2.5 (0.5 * 5, because we specified magnitude
        // of 0.5, and there are 5 categories to distribute normalized magnitudes to)
        Assert.assertTrue(sum <= 2.5);

        System.out.println(magnitudes);

    }

    @Test
    public


}