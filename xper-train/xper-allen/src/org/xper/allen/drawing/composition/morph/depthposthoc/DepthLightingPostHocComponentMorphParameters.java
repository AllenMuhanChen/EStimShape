package org.xper.allen.drawing.composition.morph.depthposthoc;

import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.NormalDistributedComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.NormalMorphDistributer;
import org.xper.allen.drawing.composition.morph.RadiusProfile;
import org.xper.allen.util.CoordinateConverter;

import javax.vecmath.Vector3d;

import static org.xper.allen.util.CoordinateConverter.*;

public class DepthLightingPostHocComponentMorphParameters implements ComponentMorphParameters {
    public DepthLightingPostHocComponentMorphParameters() {
    }

    @Override
    public Vector3d morphOrientation(Vector3d oldOrientation) {
        SphericalCoordinates oldSpherical = cartesianToSpherical(oldOrientation);
        double oldPhi = oldSpherical.theta;
        double newPhi = -oldPhi;
        SphericalCoordinates newSpherical = new SphericalCoordinates(oldSpherical.r, oldSpherical.phi, newPhi);
        return CoordinateConverter.sphericalToVector(newSpherical);
    }

    @Override
    public Double morphRotation(Double oldRotation) {
        return oldRotation;
    }

    @Override
    public Double morphCurvature(Double oldCurvature) {
        return oldCurvature;
    }

    @Override
    public Double morphLength(Double oldLength) {
        return oldLength;
    }

    @Override
    public RadiusProfile morphRadius(RadiusProfile oldRadiusProfile) {
        return oldRadiusProfile;
    }

    @Override
    public void redistribute() {

    }
}