package org.xper.allen.drawing.composition.morph;

import javax.vecmath.Vector3d;

public interface ComponentMorphParameters {
    Vector3d morphOrientation(Vector3d oldOrientation);

    Double morphRotation(Double oldRotation);

    Double morphCurvature(Double oldCurvature);

    Double morphLength(Double oldLength);

    RadiusProfile morphRadius(RadiusProfile oldRadiusProfile);

    void redistribute();
}