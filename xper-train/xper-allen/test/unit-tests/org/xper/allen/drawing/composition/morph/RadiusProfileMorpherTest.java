package org.xper.allen.drawing.composition.morph;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters.RadiusInfo;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters.RadiusProfile;

import static org.junit.Assert.*;

public class RadiusProfileMorpherTest {

    private RadiusProfileMorpher morpher;

    @Before
    public void setUp() throws Exception {
        morpher = new RadiusProfileMorpher();

    }

    /**
     * MAX_RADIUS = 3.0
     * MIN_RADIUS = 9.0/10.0 or 0.00001 depending if EndPt or not
     */
    @Test
    public void magnitude_of_one_goes_to_furthest_min_or_max() {

        RadiusProfile oldRadiusProfile = new RadiusProfile();
        oldRadiusProfile.addRadiusInfo(1, new RadiusInfo(2.5, null, ComponentMorphParameters.RADIUS_TYPE.ENDPT, true));
        Double length = 9.0;
        Double curvature = 1/6.0;

        RadiusProfile newRadiusProfile = morpher.morphRadiusProfile(oldRadiusProfile, length, curvature, 1.0);
        assertEquals(0.00001, newRadiusProfile.getRadiusInfo(1).getRadius(), 0.00001);

        oldRadiusProfile = new RadiusProfile();
        oldRadiusProfile.addRadiusInfo(1, new RadiusInfo(1.0, null, ComponentMorphParameters.RADIUS_TYPE.JUNCTION, true));

        newRadiusProfile = morpher.morphRadiusProfile(oldRadiusProfile, length, curvature, 1.0);
        assertEquals(3.0, newRadiusProfile.getRadiusInfo(1).getRadius(), 0.00001);
    }

    @Test
    public void test_magnitude_half(){
        RadiusProfile oldRadiusProfile = new RadiusProfile();
        oldRadiusProfile.addRadiusInfo(1, new RadiusInfo(2.0, null, ComponentMorphParameters.RADIUS_TYPE.JUNCTION, true));
        Double length = 9.0;
        Double curvature = 1/6.0;

        for (int i = 0; i < 100; i++) {
            RadiusProfile newRadiusProfile = morpher.morphRadiusProfile(oldRadiusProfile, length, curvature, 0.5);
            Double newRadius = newRadiusProfile.getRadiusInfo(1).getRadius();
            System.out.println(newRadius);
            assertTrue(newRadius == 1.45 || newRadius == 2.55);
        }

    }
}