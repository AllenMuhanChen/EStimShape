package org.xper.allen.drawing.composition.morph;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.composition.AllenMAxisArc;
import javax.vecmath.Vector3d;
import static org.junit.Assert.*;

public class BaseMorphParametersTest {

    private BaseMorphParameters baseMorphParameters;
    private StubAllenMAxisArc stubArc;

    private class StubAllenMAxisArc extends AllenMAxisArc {
        private Vector3d normal = new Vector3d(0, 1, 0);

        public void setNormal(Vector3d normal) {
            this.normal = normal;
        }

        @Override
        public Vector3d getNormal() {
            return this.normal;
        }
    }

    @Before
    public void setUp() {
        baseMorphParameters = new BaseMorphParameters();
        stubArc = new StubAllenMAxisArc();
    }

    @Test
    public void testMorphCurvature_StraightToCurved() {
        Double oldCurvature = 100000.0; // Straight line
        Double newCurvature = baseMorphParameters.morphCurvature(oldCurvature, stubArc);
        assertNotNull(newCurvature);
        assertTrue(newCurvature < 100000.0); // Should be curved now
    }

    @Test
    public void testMorphCurvature_CurvedToStraightOrRotated() {
        Double oldCurvature = 0.5; // Highly curved (small radius)
        Double oldRotation = 0.0;

        Double newCurvature = baseMorphParameters.morphCurvature(oldCurvature, stubArc);
        Double newRotation = baseMorphParameters.morphRotation(oldRotation);

        assertNotNull(newCurvature);
        assertNotNull(newRotation);

        System.out.println("Old curvature: " + oldCurvature + ", New curvature: " + newCurvature);
        System.out.println("Old rotation: " + oldRotation + ", New rotation: " + newRotation);

        // Check if either the curvature changed significantly or the rotation changed
        boolean curvatureChanged = Math.abs(newCurvature - oldCurvature) > 0.1 || Math.abs(newCurvature - 100000.0) < 0.001;
        boolean rotationChanged = Math.abs(newRotation - oldRotation) > 0.1;

        assertTrue("Curvature should change significantly or rotation should change",
                curvatureChanged || rotationChanged);

        if (curvatureChanged) {
            System.out.println("The component was straightened");
        }
        if (rotationChanged) {
            System.out.println("The component was rotated");
        }
    }
    @Test
    public void testMorphCurvature_MedCurvedToHighCurvedAndRotated() {
        Double oldCurvature = 4.0; // Medium curve
        Double oldRotation = 0.0;

        Double newCurvature = baseMorphParameters.morphCurvature(oldCurvature, stubArc);
        Double newRotation = baseMorphParameters.morphRotation(oldRotation);

        assertNotNull(newCurvature);
        assertNotNull(newRotation);

        System.out.println("Old curvature: " + oldCurvature + ", New curvature: " + newCurvature);
        System.out.println("Old rotation: " + oldRotation + ", New rotation: " + newRotation);

        // Check if curvature increased (more curved)
        boolean curvedMore = newCurvature < oldCurvature;

        // Check if rotation changed
        boolean rotated = !newRotation.equals(oldRotation);

        assertTrue("Curvature should increase or rotation should change", curvedMore || rotated);

        if (curvedMore) {
            System.out.println("The component became more curved");
        }
        if (rotated) {
            System.out.println("The component was rotated");
        }

        // Additional assertion to ensure some change occurred
        assertFalse("Either curvature or rotation should change",
                newCurvature.equals(oldCurvature) && newRotation.equals(oldRotation));
    }

    @Test
    public void testMorphRotation_NormalCase() {
        stubArc.setNormal(new Vector3d(0, 1, 0));
        baseMorphParameters.morphCurvature(2.0, stubArc); // This sets the new rotation
        Double newRotation = baseMorphParameters.morphRotation(0.0);
        assertNotNull(newRotation);
        assertNotEquals(0.0, newRotation.doubleValue(), 0.001);
    }

    @Test
    public void testMorphRotation_180DegreeCase() {
        stubArc.setNormal(new Vector3d(0, -1, 0)); // Opposite of the default
        baseMorphParameters.morphCurvature(2.0, stubArc);
        Double newRotation = baseMorphParameters.morphRotation(0.0);
        assertNotNull(newRotation);
        assertTrue(Math.abs(newRotation - Math.PI) < 0.001 || Math.abs(newRotation + Math.PI) < 0.001);
    }


    @Test
    public void testMorphRadius() {
        RadiusProfile oldRadiusProfile = new RadiusProfile();
        oldRadiusProfile.addRadiusInfo(1, new RadiusInfo(1.0, 1, RADIUS_TYPE.JUNCTION, false));
        oldRadiusProfile.addRadiusInfo(26, new RadiusInfo(0.8, 26, RADIUS_TYPE.MIDPT, false));
        oldRadiusProfile.addRadiusInfo(51, new RadiusInfo(0.6, 51, RADIUS_TYPE.ENDPT, false));

        RadiusProfile newRadiusProfile = baseMorphParameters.morphRadius(oldRadiusProfile);

        assertNotNull(newRadiusProfile);
        System.out.println("Old radius profile: " + oldRadiusProfile);
        System.out.println("New radius profile: " + newRadiusProfile);
        assertTrue(oldRadiusProfile.getRadiusInfo(1).getRadius().equals(newRadiusProfile.getRadiusInfo(1).getRadius()));
        assertFalse(oldRadiusProfile.getRadiusInfo(26).getRadius().equals(newRadiusProfile.getRadiusInfo(26).getRadius()));
        assertFalse(oldRadiusProfile.getRadiusInfo(51).getRadius().equals(newRadiusProfile.getRadiusInfo(51).getRadius()));
    }

    @Test
    public void testMorphOrientation() {
        Vector3d oldOrientation = new Vector3d(1, 0, 0);
        Vector3d newOrientation = baseMorphParameters.morphOrientation(oldOrientation);
        assertEquals(oldOrientation, newOrientation); // Since it's not implemented yet, it should return the same vector
    }

    @Test
    public void testMorphLength() {
        Double oldLength = 5.0;
        Double newLength = baseMorphParameters.morphLength(oldLength);
        assertEquals(oldLength, newLength); // Since it's not implemented yet, it should return the same value
    }
}