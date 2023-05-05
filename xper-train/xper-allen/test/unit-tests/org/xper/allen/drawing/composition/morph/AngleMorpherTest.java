package org.xper.allen.drawing.composition.morph;

import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.*;

public class AngleMorpherTest {

    private AngleMorpher morpher;

    @Before
    public void setUp() throws Exception {
        morpher = new AngleMorpher();
    }

    @Test
    public void zero_rotation_magnitude_leads_to_no_rotation() {
        Double oldRotation = 0.0;
        Double rotationMagnitude = 0.0;
        Double newRotation = morpher.morphAngle(oldRotation, rotationMagnitude);
        assertEquals(newRotation, oldRotation, 0.0001);
    }
    @Test
    public void half_rotation_magnitude_leads_to_90_degree_rotation() {
        Double oldRotation = 0.0;
        Double rotationMagnitude = 0.5;
        Double newRotation = morpher.morphAngle(oldRotation, rotationMagnitude);
        assertEquals(Math.abs(newRotation-oldRotation), Math.PI/2, 0.0001);
    }
}