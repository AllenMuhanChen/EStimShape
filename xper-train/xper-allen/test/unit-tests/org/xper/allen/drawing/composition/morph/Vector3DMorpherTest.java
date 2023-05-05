package org.xper.allen.drawing.composition.morph;

import org.junit.Before;
import org.junit.Test;

import javax.vecmath.Vector3d;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

public class Vector3DMorpherTest {

    private Vector3DMorpher morpher;

    @Before
    public void setUp() throws Exception {
        morpher = new Vector3DMorpher();
    }

    @Test
    public void magnitude_one_flips_by_180() {
        Vector3d oldVector = new Vector3d(1, 0, 0);
        Vector3d newVector = morpher.morphVector(oldVector, 1);

        assertEquals(-1, newVector.x, 0.0001);
        assertEquals(0, newVector.y, 0.0001);
        assertEquals(0, newVector.z, 0.0001);

    }

    @Test
    public void magnitude_half_flips_by_90_in_random_direction() {

        int numAttempts = 100;
        List<Vector3d> newVectors = new ArrayList<>();

        // Check that the new vectors are 90 degrees from the old vector
        for (int i = 0; i < numAttempts; i++) {
            Vector3d oldVector = new Vector3d(1, 0, 0);
            Vector3d newVector = morpher.morphVector(oldVector, 0.5);
            newVectors.add(newVector);
            System.out.println("newVector = " + newVector);
            assertEquals(Math.PI/2, oldVector.angle(newVector), 0.0001);
        }

        // Check that the new vectors are not all the same
        for (int i=1; i<newVectors.size(); i++) {
            assertNotEquals(newVectors.get(i).x == newVectors.get(i-1).x, 0.0001);
            assertNotEquals(newVectors.get(i).y == newVectors.get(i-1).y, 0.0001);
            assertNotEquals(newVectors.get(i).z == newVectors.get(i-1).z, 0.0001);
        }
    }
}