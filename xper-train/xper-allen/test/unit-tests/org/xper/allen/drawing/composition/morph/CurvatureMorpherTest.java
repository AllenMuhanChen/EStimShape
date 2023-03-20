package org.xper.allen.drawing.composition.morph;

import org.junit.Before;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;
import static org.xper.allen.drawing.composition.morph.CurvatureMorpher.*;

public class CurvatureMorpherTest {

    private CurvatureMorpher morpher;

    @Before
    public void setUp() throws Exception {
        morpher = new CurvatureMorpher();

    }

    @Test
    public void magnitude_of_one_leads_to_max_possible_curvature_change() {
        Double oldCurvature = 1.0/10000;
        Double curvatureMagnitude = 1.0;
        Double newCurvature = morpher.morphCurvature(oldCurvature, curvatureMagnitude);
        assertEquals(newCurvature, 1.0, 0.0001);
    }

    /**
     * oldCurvature should be dead center of med curvature
     */
    @Test
    public void intermediate_magnitude(){
        Double oldCurvature = 11/60.0;
        Double curvatureMagnitude = 0.25;
        Double newCurvature = morpher.morphCurvature(oldCurvature, curvatureMagnitude);

        List<Double> newCurvatures = new ArrayList<>();
        for (int i=0; i<100; i++) {
            newCurvature = morpher.morphCurvature(oldCurvature, curvatureMagnitude);
            System.out.println(newCurvature);
        }

    }
}