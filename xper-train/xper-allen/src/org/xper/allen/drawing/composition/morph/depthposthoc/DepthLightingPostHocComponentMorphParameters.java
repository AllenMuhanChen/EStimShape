package org.xper.allen.drawing.composition.morph.depthposthoc;

import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.NormalDistributedComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.NormalMorphDistributer;
import org.xper.allen.drawing.composition.morph.RadiusProfile;

import javax.vecmath.Vector3d;

public class DepthLightingPostHocComponentMorphParameters implements ComponentMorphParameters {
    @Override
    public Vector3d morphOrientation(Vector3d oldOrientation) {
        return null;
    }

    @Override
    public Double morphRotation(Double oldRotation) {
        return null;
    }

    @Override
    public Double morphCurvature(Double oldCurvature) {
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
    public void redistribute() {

    }
}