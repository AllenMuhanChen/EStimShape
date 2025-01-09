package org.xper.allen.drawing.composition.morph.depthposthoc;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.morph.*;
import sun.reflect.generics.reflectiveObjects.NotImplementedException;

import javax.vecmath.Vector3d;

public class DepthLightingPostHocComponentMorphParameters implements ComponentMorphParameters {
    public DepthLightingPostHocComponentMorphParameters() {
    }

    @Override
    public Vector3d morphOrientation(Vector3d oldOrientation) {
//        SphericalCoordinates oldSpherical = cartesianToSpherical(oldOrientation);
//        double oldPhi = oldSpherical.theta;
//        double newPhi = -oldPhi;
//        SphericalCoordinates newSpherical = new SphericalCoordinates(oldSpherical.r, oldSpherical.phi, newPhi);
//        return CoordinateConverter.sphericalToVector(newSpherical);
        Vector3d newOrientation = new Vector3d(oldOrientation);
        newOrientation.z = -oldOrientation.z;
        return newOrientation;
    }

    @Override
    public Double morphRotation(Double oldRotation) {
        return oldRotation;
    }

    @Override
    public Double morphCurvature(Double oldCurvature, AllenMAxisArc arcToMorph) {
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
    public void distribute() {

    }

    @Override
    public ComponentMorphData getMorphData() {
        throw new NotImplementedException();
    }
}