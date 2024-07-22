package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.metricmorphs.LengthMetricMorphMagnitude;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphOrientation;
import org.xper.allen.drawing.composition.metricmorphs.SizeMetricMorphMagnitude;
import org.xper.allen.drawing.composition.metricmorphs.CurvatureMetricMorphMagnitude;
import org.xper.allen.drawing.composition.metricmorphs.RotationMetricMorphMagnitude;

import javax.vecmath.Vector3d;
import java.util.Map;

public class SetMorphParameters implements ComponentMorphParameters {
    private SizeMetricMorphMagnitude thicknessMorph;
    private LengthMetricMorphMagnitude lengthMorph;
    private MetricMorphOrientation orientationMorph;
    private CurvatureMetricMorphMagnitude curvatureMorph;
    private RotationMetricMorphMagnitude rotationMorph;

    //flags
    boolean doThickness;
    boolean doLength;
    boolean doOrientation;

    public SetMorphParameters() {
        thicknessMorph = new SizeMetricMorphMagnitude();
        lengthMorph = new LengthMetricMorphMagnitude(10);
        orientationMorph = new MetricMorphOrientation();




        // Set default values for percent changes
        thicknessMorph.percentChangeLowerBound = 0.22;
        thicknessMorph.percentChangeUpperBound = 0.24;
        lengthMorph.percentChangeLowerBound = 0.10;
        lengthMorph.percentChangeUpperBound = 0.15;
        orientationMorph.setAngleChangeLowerBound(20 * Math.PI / 180);
        orientationMorph.setAngleChangeUpperBound(30 * Math.PI / 180);
        curvatureMorph.setPercentChangeLowerBound(0.5);
        rotationMorph.percentChangeLowerBound = 0.025;
        rotationMorph.percentChangeUpperBound = 0.05;
    }

    @Override
    public Vector3d morphOrientation(Vector3d oldOrientation) {
        orientationMorph.setOldVector(oldOrientation);
        return orientationMorph.calculateVector();
    }

    @Override
    public Double morphCurvature(Double oldCurvature, AllenMAxisArc arcToMorph) {
        curvatureMorph.setOldValue(oldCurvature);
        return curvatureMorph.calculateMagnitude(arcToMorph);
    }

    @Override
    public Double morphRotation(Double oldRotation) {
        rotationMorph.oldValue = oldRotation;
        return rotationMorph.calculateMagnitude();
    }

    @Override
    public Double morphLength(Double oldLength) {
        return lengthMorph.calculateMagnitude(oldLength);
    }

    @Override
    public RadiusProfile morphRadius(RadiusProfile oldRadiusProfile) {
        Map<Integer, RadiusInfo> oldRadiusInfoForPoints = oldRadiusProfile.getInfoForRadius();

        // Find the junction, midpoint, and endpoint radii
        RadiusInfo junctionInfo = null;
        RadiusInfo midpointInfo = null;
        RadiusInfo endpointInfo = null;

        for (RadiusInfo info : oldRadiusInfoForPoints.values()) {
            switch (info.getRadiusType()) {
                case JUNCTION:
                    junctionInfo = info;
                    break;
                case MIDPT:
                    midpointInfo = info;
                    break;
                case ENDPT:
                    endpointInfo = info;
                    break;
            }
        }

        if (junctionInfo == null || midpointInfo == null || endpointInfo == null) {
            throw new IllegalArgumentException("Old radius profile is missing necessary information");
        }

        // Calculate original thickness (normalization factor)
        double originalThickness = Math.max(junctionInfo.getRadius(),
                Math.max(midpointInfo.getRadius(), endpointInfo.getRadius()));

        double newThickness = originalThickness;
        if (doThickness) {
            newThickness = thicknessMorph.calculateMagnitude(originalThickness);
            // Calculate new thickness (normalized by original thickness
        }

        // Calculate normalized radii
        double normalizedJunc = junctionInfo.getRadius() / originalThickness;
        double normalizedMid = midpointInfo.getRadius() / originalThickness;
        double normalizedEnd = endpointInfo.getRadius() / originalThickness;

        // Create new radius profile
        RadiusProfile newRadiusProfile = new RadiusProfile();
        newRadiusProfile.addRadiusInfo(junctionInfo.getuNdx(),
                new RadiusInfo(normalizedJunc * originalThickness, junctionInfo.getuNdx(), RADIUS_TYPE.JUNCTION, false));
        newRadiusProfile.addRadiusInfo(midpointInfo.getuNdx(),
                new RadiusInfo(normalizedMid * newThickness, midpointInfo.getuNdx(), RADIUS_TYPE.MIDPT, false));
        newRadiusProfile.addRadiusInfo(endpointInfo.getuNdx(),
                new RadiusInfo(normalizedEnd * newThickness, endpointInfo.getuNdx(), RADIUS_TYPE.ENDPT, false));

        return newRadiusProfile;
    }

    @Override
    public void distribute() {
        // This method is not used in this implementation
    }

    // Getters and setters for the morph parameters can be added here if needed
}