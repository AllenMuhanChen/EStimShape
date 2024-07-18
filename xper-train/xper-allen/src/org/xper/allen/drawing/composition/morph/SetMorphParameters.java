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

    public SetMorphParameters(double maxImageDimensionDegrees) {
        thicknessMorph = new SizeMetricMorphMagnitude();
        lengthMorph = new LengthMetricMorphMagnitude(maxImageDimensionDegrees / 2);
        orientationMorph = new MetricMorphOrientation();
        curvatureMorph = new CurvatureMetricMorphMagnitude(maxImageDimensionDegrees);
        rotationMorph = new RotationMetricMorphMagnitude();

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
//        RadiusProfile newProfile = new RadiusProfile();
//        for (Map.Entry<Integer, RadiusInfo> entry : oldRadiusProfile.getInfoForRadius().entrySet()) {
//            RadiusInfo oldInfo = entry.getValue();
////            double newRadius = thicknessMorph.calculateMagnitude(oldRadiusProfile);
////            RadiusInfo newInfo = new RadiusInfo(newRadius, oldInfo.getuNdx(), oldInfo.getRadiusType(), oldInfo.getPreserve());
////            newProfile.addRadiusInfo(entry.getKey(), newInfo);
//        }
//        return newProfile;
    }

    @Override
    public void distribute() {
        // This method is not used in this implementation
    }

    // Getters and setters for the morph parameters can be added here if needed
}