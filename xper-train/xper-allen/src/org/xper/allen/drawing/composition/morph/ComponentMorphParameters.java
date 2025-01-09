package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.AllenMAxisArc;

import javax.vecmath.Vector3d;

public interface ComponentMorphParameters<T> {
    Vector3d morphOrientation(Vector3d oldOrientation);

    /**
     * moprhCurvature is called before morphRotation, so if there is any
     * dependence between curvature and rotation, then this should be implemented
     * via class fields.
     *
     * @param oldCurvature
     * @param arcToMorph
     * @return
     */
    Double morphCurvature(Double oldCurvature, AllenMAxisArc arcToMorph);

    Double morphRotation(Double oldRotation);

    Double morphLength(Double oldLength);

    RadiusProfile morphRadius(RadiusProfile oldRadiusProfile);

    void distribute();

    T getMorphData();
}