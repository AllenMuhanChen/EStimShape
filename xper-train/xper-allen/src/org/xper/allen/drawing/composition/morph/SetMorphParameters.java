package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import javax.vecmath.Vector3d;
import java.util.Map;
import java.util.Random;

public class SetMorphParameters implements ComponentMorphParameters {
    // Morphing parameters
    private double thicknessPercentChange;
    private double thicknessMin;
    private double thicknessMax;

    private double lengthPercentChange;
    private double lengthMin;
    private double lengthMax;
    private double rad;

    private double orientationAngleChange;
    private double orientationAngleMin;
    private double orientationAngleMax;

    // Flags for which morphs to apply
    private boolean doThickness;
    private boolean doLength;
    private boolean doOrientation;

    // Number of morphs to apply
    private int numberOfMorphs;

    private Random random = new Random();

    private double arcLength;

    public SetMorphParameters() {
        // Set default values
        thicknessPercentChange = 0.5;
        thicknessMin = 0.5;
        thicknessMax = 2.0;

        lengthPercentChange = 0.50;
        lengthMin = 1.5;

        orientationAngleChange = Math.PI / 4;
        orientationAngleMin = 0;
        orientationAngleMax = Math.PI * 2;

        numberOfMorphs = 2;
    }

    @Override
    public Vector3d morphOrientation(Vector3d oldOrientation) {
        if (!doOrientation) return oldOrientation;

        double angle = Math.acos(oldOrientation.z);
        double phi = Math.atan2(oldOrientation.y, oldOrientation.x);

        double change = (random.nextDouble() * 2 - 1) * orientationAngleChange;
        angle += change;
        angle = Math.max(orientationAngleMin, Math.min(orientationAngleMax, angle));

        double sinAngle = Math.sin(angle);
        return new Vector3d(
                sinAngle * Math.cos(phi),
                sinAngle * Math.sin(phi),
                Math.cos(angle)
        );
    }

    @Override
    public Double morphCurvature(Double oldCurvature, AllenMAxisArc arcToMorph) {
        this.rad = arcToMorph.getRad();
        this.arcLength = arcToMorph.getArcLen();
        this.lengthMax = Math.min(Math.PI * rad, 5);

        return oldCurvature;  // Not changing curvature
    }

    @Override
    public Double morphRotation(Double oldRotation) {
        return oldRotation;  // Not changing rotation
    }

    @Override
    public Double morphLength(Double oldLength) {
        if (!doLength) return oldLength;

        double percentChange = (random.nextDouble() * 2 - 1) * lengthPercentChange;
        double newLength = oldLength * (1 + percentChange);
        return Math.max(lengthMin, Math.min(lengthMax, newLength));
    }

    @Override
    public RadiusProfile morphRadius(RadiusProfile oldRadiusProfile) {
        if (!doThickness) return oldRadiusProfile;

        RadiusProfile newRadiusProfile = new RadiusProfile();
        double percentChange = (random.nextDouble() * 2 - 1) * thicknessPercentChange;

        for (Map.Entry<Integer, RadiusInfo> entry : oldRadiusProfile.getInfoForRadius().entrySet()) {
            RadiusInfo oldInfo = entry.getValue();
            double newRadius = oldInfo.getRadius() * (1 + percentChange);

            double rMin, rMax;
            if (oldInfo.getRadiusType() == RADIUS_TYPE.ENDPT) {
                rMin = 0.00001;
                rMax = Math.min(arcLength / 3.0, 0.5 * rad);
            } else {  // JUNCTION or MIDPT
                rMin = arcLength / 10.0;
                rMax = Math.min(arcLength / 3.0, 0.5 * rad);
            }

            newRadius = Math.max(rMin, Math.min(rMax, newRadius));

            RadiusInfo newInfo = new RadiusInfo(newRadius, oldInfo.getuNdx(), oldInfo.getRadiusType(), oldInfo.getPreserve());
            newRadiusProfile.addRadiusInfo(entry.getKey(), newInfo);
        }

        return newRadiusProfile;
    }

    @Override
    public void distribute() {
        doThickness = doLength = doOrientation = false;

        for (int i = 0; i < numberOfMorphs; i++) {
            int choice = random.nextInt(3);
            switch (choice) {
                case 0: doThickness = true; break;
                case 1: doLength = true; break;
                case 2: doOrientation = true; break;
            }
        }
    }

    // Getters and setters
    public void setThicknessParameters(double percentChange, double min, double max) {
        this.thicknessPercentChange = percentChange;
        this.thicknessMin = min;
        this.thicknessMax = max;
    }

    public void setLengthParameters(double percentChange, double min, double max) {
        this.lengthPercentChange = percentChange;
        this.lengthMin = min;
        this.lengthMax = max;
    }

    public void setOrientationParameters(double angleChange, double min, double max) {
        this.orientationAngleChange = angleChange;
        this.orientationAngleMin = min;
        this.orientationAngleMax = max;
    }

    public void setNumberOfMorphs(int number) {
        this.numberOfMorphs = number;
    }
}