package org.xper.allen.drawing.composition.morph;

import javax.vecmath.Vector3d;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

public class ComponentMorphParameters {

    public static double MAX;
    Double magnitude;

    public ComponentMorphParameters(Double magnitude) {
        this.magnitude = magnitude;

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
        LengthMorpher doubleMorpher = new LengthMorpher();
        length = doubleMorpher.morphLength(oldLength, curvature, lengthMagnitude);
        return length;
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

        Collections.shuffle(magnitudes);

        Double amountToDistribute = magnitude;
        for (AtomicReference<Double> magnitude : magnitudes) {
            double randomMagnitude = Math.random() * MAX;
            amountToDistribute -= randomMagnitude;
            if (amountToDistribute > 0) {
                double normalizedMagnitude = randomMagnitude / MAX;
                magnitude.set(normalizedMagnitude);
            }
            else {
                magnitude.set(amountToDistribute + randomMagnitude);
                break;
            }
        }

        this.orientationMagnitude = orientationMagnitude.get();
        this.rotationMagnitude = rotationMagnitude.get();
        this.lengthMagnitude = lengthMagnitude.get();
        this.curvatureMagnitude = curvatureMagnitude.get();
        this.radiusProfileMagnitude = radiusProfileMagnitude.get();
    }

    public static class RadiusProfile {
    }




}