package org.xper.allen.drawing.ga;

import org.junit.Test;
import org.xper.drawing.Coordinates2D;

import java.util.Arrays;
import java.util.List;

import static org.junit.Assert.*;

public class ConcaveHullReceptiveFieldTest {

    @Test
    public void testConcaveHull() {

        //Arrowhead shape with tip at (0, 2) and base at (-1, 0), (1, 0), (0, 1)
        List<Coordinates2D> hullPoints = Arrays.asList(
                new Coordinates2D(1, 0),
                new Coordinates2D(0, 2),
                new Coordinates2D(-1, 0),
                new Coordinates2D(0, 1));

        ConcaveHullReceptiveField concaveHullReceptiveField = new ConcaveHullReceptiveField(hullPoints);

        // Test the case where the point is outside the hull
        assertFalse(concaveHullReceptiveField.isInRF(0, 0));
        assertFalse(concaveHullReceptiveField.isInRF(0, 2.5));
        assertFalse(concaveHullReceptiveField.isInRF(0, -1.0001));
        assertFalse(concaveHullReceptiveField.isInRF(1.00001, 0));

        // Test the case where the point is inside the hull
        assertTrue(concaveHullReceptiveField.isInRF(0, 1.5));
        assertTrue(concaveHullReceptiveField.isInRF(0, 1.999));
        assertTrue(concaveHullReceptiveField.isInRF(0.999, 0.0015));
        assertTrue(concaveHullReceptiveField.isInRF(-0.999, 0.0015));
    }

    @Test
    public void testConvexHull(){
        //Square shape with vertices at (0, 0), (0, 1), (1, 1), (1, 0)
        List<Coordinates2D> hullPoints = Arrays.asList(
                new Coordinates2D(0, 0),
                new Coordinates2D(0, 1),
                new Coordinates2D(1, 1),
                new Coordinates2D(1, 0));

        ConcaveHullReceptiveField concaveHullReceptiveField = new ConcaveHullReceptiveField(hullPoints);

        // Test the case where the point is outside the hull
        assertFalse(concaveHullReceptiveField.isInRF(0, -0.0001));
        assertFalse(concaveHullReceptiveField.isInRF(0, 1.0001));
        assertFalse(concaveHullReceptiveField.isInRF(-0.0001, 0));
        assertFalse(concaveHullReceptiveField.isInRF(1.0001, 0));

        // Test the case where the point is inside the hull
        assertTrue(concaveHullReceptiveField.isInRF(0.5, 0.5));
        assertTrue(concaveHullReceptiveField.isInRF(0.0001, 0.0001));
        assertTrue(concaveHullReceptiveField.isInRF(0.9999, 0.9999));
        assertTrue(concaveHullReceptiveField.isInRF(0.9999, 0.0001));
    }
}