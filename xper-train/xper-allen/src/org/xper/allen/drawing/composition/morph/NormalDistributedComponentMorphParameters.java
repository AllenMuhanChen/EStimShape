package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.AllenMAxisArc;

import javax.vecmath.Vector3d;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

public class NormalDistributedComponentMorphParameters implements ComponentMorphParameters {

    private double maxOrientationChange = -1;
    public Double magnitude;
    private NormalMorphDistributer normalMorphDistributer;

    public NormalDistributedComponentMorphParameters(Double magnitude, NormalMorphDistributer normalMorphDistributer) {
        this.magnitude = magnitude;
        this.normalMorphDistributer = normalMorphDistributer;

        distributeMagnitude();
    }

    public NormalDistributedComponentMorphParameters(Double magnitude, NormalMorphDistributer normalMorphDistributer, double maxRotationRadians) {
        this.magnitude = magnitude;
        this.normalMorphDistributer = normalMorphDistributer;
        this.maxOrientationChange = maxRotationRadians;
        distributeMagnitude();
    }

    public void distribute() {
        distributeMagnitude();
    }


    Vector3d orientation;
    Double rotation;
    Double length;
    Double curvature;
    RadiusProfile radiusProfile;

    @Override
    public Vector3d morphOrientation(Vector3d oldOrientation){
        Vector3DMorpher vector3DMorpher;
        if (maxOrientationChange != -1){
            vector3DMorpher = new Vector3DMorpher(maxOrientationChange);
        } else{
            vector3DMorpher = new Vector3DMorpher();
        }

        orientation = vector3DMorpher.morphVector(oldOrientation, orientationMagnitude);
        return orientation;
    }

    @Override
    public Double morphCurvature(Double oldCurvature, AllenMAxisArc arcToMorph){
        CurvatureMorpher curvatureMorpher = new CurvatureMorpher();
        curvature = curvatureMorpher.morphCurvature(oldCurvature, curvatureMagnitude);
        return curvature;
    }

    @Override
    public Double morphRotation(Double oldRotation){
        AngleMorpher angleMorpher = new AngleMorpher();
        rotation = angleMorpher.morphAngle(oldRotation, rotationMagnitude);
        return rotation;
    }

    @Override
    public Double morphLength(Double oldLength){
        if (curvature == null) {
            throw new RuntimeException("Curvature must be set before length can be set. Call getCurvature() first.");
        }
        LengthMorpher doubleMorpher = new LengthMorpher();
        length = doubleMorpher.morphLength(oldLength, curvature, lengthMagnitude);
        return length;
    }

    @Override
    public RadiusProfile morphRadius(RadiusProfile oldRadiusProfile){
        RadiusProfileMorpher radiusProfileMorpher = new RadiusProfileMorpher();
        radiusProfile = radiusProfileMorpher.morphRadiusProfile(oldRadiusProfile, length, curvature, radiusProfileMagnitude);
        return radiusProfile;
    }

    Double orientationMagnitude;
    Double rotationMagnitude;
    Double lengthMagnitude;
    Double curvatureMagnitude;
    Double radiusProfileMagnitude;

    private void distributeMagnitude() {
        AtomicReference<Double> orientationMagnitude = new AtomicReference<>(0.0);
        AtomicReference<Double> rotationMagnitude = new AtomicReference<>(0.0);
        AtomicReference<Double> lengthMagnitude = new AtomicReference<>(0.0);
        AtomicReference<Double> curvatureMagnitude = new AtomicReference<>(0.0);
        AtomicReference<Double> radiusProfileMagnitude = new AtomicReference<>(0.0);

        List<AtomicReference<Double>> magnitudes = new ArrayList<>();
        magnitudes.add(orientationMagnitude);
        magnitudes.add(rotationMagnitude);
        magnitudes.add(lengthMagnitude);
        magnitudes.add(curvatureMagnitude);
        magnitudes.add(radiusProfileMagnitude);

        normalMorphDistributer.distributeMagnitudeTo(magnitudes, magnitude);



        this.orientationMagnitude = orientationMagnitude.get();
        this.rotationMagnitude = rotationMagnitude.get();
        this.lengthMagnitude = lengthMagnitude.get();
        this.curvatureMagnitude = curvatureMagnitude.get();
        this.radiusProfileMagnitude = radiusProfileMagnitude.get();
    }


    @Override
    public ComponentMorphData getMorphData() {
        return new ComponentMorphData(orientationMagnitude, rotationMagnitude, lengthMagnitude, curvatureMagnitude, radiusProfileMagnitude);
    }

    public Vector3d getOrientation() {
        return orientation;
    }

    public Double getRotation() {
        return rotation;
    }

    public Double getLength() {
        return length;
    }

    public Double getCurvature() {
        return curvature;
    }

    public RadiusProfile getRadiusProfile() {
        return radiusProfile;
    }

    public String toString() {
        return "Orientation: " + orientation + " Rotation: " + rotation + " Length: " + length + " Curvature: " + curvature + " RadiusProfile: " + radiusProfile;
    }

}