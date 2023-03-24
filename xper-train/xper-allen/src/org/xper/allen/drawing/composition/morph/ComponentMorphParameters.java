package org.xper.allen.drawing.composition.morph;

import javax.vecmath.Vector3d;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

public class ComponentMorphParameters {

    public static double MAX;
    public Double magnitude;

    public ComponentMorphParameters(Double magnitude) {
        this.magnitude = magnitude;

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

    public Vector3d getOrientation(Vector3d oldOrientation){
        Vector3DMorpher vector3DMorpher = new Vector3DMorpher();
        orientation = vector3DMorpher.morphVector(oldOrientation, orientationMagnitude);
        return orientation;
    }

    public Double getRotation(Double oldRotation){
        AngleMorpher angleMorpher = new AngleMorpher();
        rotation = angleMorpher.morphAngle(oldRotation, rotationMagnitude);
        return rotation;
    }

    public Double getCurvature(Double oldCurvature){
        CurvatureMorpher curvatureMorpher = new CurvatureMorpher();
        curvature = curvatureMorpher.morphCurvature(oldCurvature, curvatureMagnitude);
        return curvature;
    }

    public Double getLength(Double oldLength){
        if (curvature == null) {
            throw new RuntimeException("Curvature must be set before length can be set. Call getCurvature() first.");
        }
        LengthMorpher doubleMorpher = new LengthMorpher();
        length = doubleMorpher.morphLength(oldLength, curvature, lengthMagnitude);
        return length;
    }

    public RadiusProfile getRadius(RadiusProfile oldRadiusProfile){
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
        MAX = 1.0 / magnitudes.size();



        Double amountLeftToDistribute = magnitude;
        while (amountLeftToDistribute > 0) {
            Collections.shuffle(magnitudes);
            for (AtomicReference<Double> magnitude : magnitudes) {
                double randomMagnitude = Math.min(Math.random() * MAX, Math.random() * this.magnitude / magnitudes.size());
                // If the random magnitude is greater than the amount left to distribute, then we need to
                // reduce the magnitude to the amount left to distribute
                if (randomMagnitude > amountLeftToDistribute) {
                    randomMagnitude = amountLeftToDistribute;
                }
                // If adding the random magnitude to the current magnitude would exceed the max, then we need to
                // reduce the magnitude to the amount that would bring the current magnitude to the max
                if (magnitude.get() + randomMagnitude > MAX) {
                    randomMagnitude = MAX - magnitude.get();                }
                double normalizedMagnitude = randomMagnitude / MAX;
                magnitude.set(magnitude.get() + randomMagnitude);
                amountLeftToDistribute -= randomMagnitude;
            }
        }

        // Normalize the magnitudes
        for (AtomicReference<Double> magnitude : magnitudes) {
            magnitude.set(magnitude.get() / MAX);
        }

        this.orientationMagnitude = orientationMagnitude.get();
        this.rotationMagnitude = rotationMagnitude.get();
        this.lengthMagnitude = lengthMagnitude.get();
        this.curvatureMagnitude = curvatureMagnitude.get();
        this.radiusProfileMagnitude = radiusProfileMagnitude.get();
    }

    public static class RadiusProfile{
        Map<Integer, RadiusInfo> infoForRadius = new HashMap<>();

        //TODO: API to add radius info

        public Map<Integer, RadiusInfo> getInfoForRadius() {
            return infoForRadius;
        }

        public void addRadiusInfo(Integer id, RadiusInfo radiusInfo){
            infoForRadius.put(id, radiusInfo);
        }

        public RadiusInfo getRadiusInfo(Integer id){
            return infoForRadius.get(id);
        }
    }
    public enum RADIUS_TYPE{JUNCTION, MIDPT, ENDPT}


    public static class RadiusInfo {
        Double radius;
        Integer uNdx;
        RADIUS_TYPE radiusType;
        Boolean preserve;

        public RadiusInfo(Double radius, Integer uNdx, RADIUS_TYPE radiusType, Boolean preserve) {
            this.radius = radius;
            this.uNdx = uNdx;
            this.radiusType = radiusType;
            this.preserve = preserve;
        }

        public RadiusInfo(RadiusInfo oldRadiusInfo, Double newRadius) {
            this.radius = newRadius;
            this.uNdx = oldRadiusInfo.getuNdx(); //not needed?
            this.radiusType = oldRadiusInfo.getRadiusType();
            this.preserve = oldRadiusInfo.getPreserve(); //not needed?
        }

        public Double getRadius() {
            return radius;
        }

        public void setRadius(Double radius) {
            this.radius = radius;
        }

        public Integer getuNdx() {
            return uNdx;
        }

        public void setuNdx(Integer uNdx) {
            this.uNdx = uNdx;
        }

        public RADIUS_TYPE getRadiusType() {
            return radiusType;
        }

        public void setRadiusType(RADIUS_TYPE radiusType) {
            this.radiusType = radiusType;
        }

        public Boolean getPreserve() {
            return preserve;
        }

        public void setPreserve(Boolean preserve) {
            this.preserve = preserve;
        }
    }
}