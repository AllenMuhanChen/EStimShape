package org.xper.allen.drawing.composition.morph;

import org.junit.Before;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

public class LengthMorpherTest {

    private LengthMorpher morpher;

    @Before
    public void setUp() throws Exception {
        morpher = new LengthMorpher();
    }

    @Test
    public void magnitude_of_zero_leads_to_same(){
        Double oldLength = 2.0;
        Double lengthMagnitude = 0.0;
        Double radius = 1.0;

        Double newLength = morpher.morphLength(oldLength, radius, lengthMagnitude);
        assertEquals(newLength, oldLength, 0.0001);
    }
    /**
     * min: 1.5
     * max: 3.14159
     */
    @Test
    public void magnitude_of_one_leads_to_farthest_min_or_max() {
        Double lengthMagnitude = 1.0;
        Double radius = 1.0;

        Double oldLength = 2.0;
        Double newLength = morpher.morphLength(oldLength, radius, lengthMagnitude);
        assertEquals(newLength, Math.PI, 0.0001);

        oldLength = 3.0;
        newLength = morpher.morphLength(oldLength, radius, lengthMagnitude);
        assertEquals(newLength, 1.5, 0.0001);
    }

    /**
     * min: 1.5
     * max: 5.0
     */
    @Test
    public void intermediate_magnitude_leads_to_random_intermediate_length(){
        double lengthMagnitude = 0.5;
        double radius = 5.0;

        List<Double> newLengths = new ArrayList<>();
        for (int i=0; i<100; i++) {
            double oldLength = (1.5 + 5.0) / 2;
            double newLength = morpher.morphLength(oldLength, radius, lengthMagnitude);

            assertTrue(newLength == 2.375 || newLength == 4.125);
            assertEquals(Math.abs(newLength-oldLength), 0.875, 0.0001);
            newLengths.add(Math.abs(newLength));
        }

        assertTrue(newLengths.contains(4.125) && newLengths.contains(2.375));

    }
}