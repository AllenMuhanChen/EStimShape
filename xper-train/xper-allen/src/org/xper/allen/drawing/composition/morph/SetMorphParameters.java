package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.metricmorphs.LengthMetricMorphMagnitude;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphOrientation;
import org.xper.allen.drawing.composition.metricmorphs.SizeMetricMorphMagnitude;

import javax.vecmath.Vector3d;

public class SetMorphParameters implements ComponentMorphParameters{
    private SizeMetricMorphMagnitude thicknessMorph;
    private LengthMetricMorphMagnitude lengthMorph;
    private MetricMorphOrientation orientationMorph;

    @Override
    public Vector3d morphOrientation(Vector3d oldOrientation) {
        return null;
    }

    @Override
    public Double morphCurvature(Double oldCurvature, AllenMAxisArc arcToMorph) {
        return null;
    }

    @Override
    public Double morphRotation(Double oldRotation) {
        return null;
    }

    @Override
    public Double morphLength(Double oldLength) {
        return null;
    }

    @Override
    public RadiusProfile morphRadius(RadiusProfile oldRadiusProfile) {
        return null;
    }

    @Override
    public void distribute() {

    }
}