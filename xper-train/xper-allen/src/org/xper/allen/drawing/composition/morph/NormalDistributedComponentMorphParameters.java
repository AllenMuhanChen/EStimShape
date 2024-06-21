package org.xper.allen.drawing.composition.morph;

import javax.vecmath.Vector3d;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

public class NormalDistributedComponentMorphParameters implements ComponentMorphParameters {

    public Double magnitude;
    private NormalMorphDistributer normalMorphDistributer;

    public NormalDistributedComponentMorphParameters(Double magnitude, NormalMorphDistributer normalMorphDistributer) {
        this.magnitude = magnitude;
        this.normalMorphDistributer = normalMorphDistributer;

        distributeMagnitude();
    }

    public void redistribute() {
        distributeMagnitude();
    }

    Vector3d orientation;
    Double rotation;
    Double length;
    Double curvature;
    RadiusProfile radiusProfile;

    @Override
    public Vector3d morphOrientation(Vector3d oldOrientation){
        Vector3DMorpher vector3DMorpher = new Vector3DMorpher();
        orientation = vector3DMorpher.morphVector(oldOrientation, orientationMagnitude);
        return orientation;
    }

    @Override
    public Double morphRotation(Double oldRotation){
        AngleMorpher angleMorpher = new AngleMorpher();
        rotation = angleMorpher.morphAngle(oldRotation, rotationMagnitude);
        return rotation;
    }

    @Override
    public Double morphCurvature(Double oldCurvature){
        CurvatureMorpher curvatureMorpher = new CurvatureMorpher();
        curvature = curvatureMorpher.morphCurvature(oldCurvature, curvatureMagnitude);
        return curvature;
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

    public void redistributeRotationMagntiude(){
        AtomicReference<Double> orientationMagnitude = new AtomicReference<>(this.orientationMagnitude);
        AtomicReference<Double> rotationMagnitude = new AtomicReference<>(this.rotationMagnitude);
        AtomicReference<Double> lengthMagnitude = new AtomicReference<>(this.lengthMagnitude);
        AtomicReference<Double> curvatureMagnitude = new AtomicReference<>(this.curvatureMagnitude);
        AtomicReference<Double> radiusProfileMagnitude = new AtomicReference<>(this.radiusProfileMagnitude);

        List<AtomicReference<Double>> magnitudes = new ArrayList<>();
        magnitudes.add(orientationMagnitude);
        magnitudes.add(lengthMagnitude);
        magnitudes.add(radiusProfileMagnitude);


        Double amountOfRotationMagnitudeToRedistribute = rotationMagnitude.get();
        Double amountToRedistribute = amountOfRotationMagnitudeToRedistribute/magnitudes.size();

        normalMorphDistributer.distributeMagnitudeTo(magnitudes, amountToRedistribute);

        this.orientationMagnitude = orientationMagnitude.get();
        this.lengthMagnitude = lengthMagnitude.get();
        this.radiusProfileMagnitude = radiusProfileMagnitude.get();
        this.curvatureMagnitude = curvatureMagnitude.get();
        this.rotationMagnitude = 0.0;

    }

    public enum RADIUS_TYPE{JUNCTION, MIDPT, ENDPT}

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