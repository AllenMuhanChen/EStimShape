package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.metricmorphs.LengthMetricMorphMagnitude;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphOrientation;
import org.xper.allen.drawing.composition.qualitativemorphs.Bin;
import org.xper.allen.drawing.composition.qualitativemorphs.CurvatureRotationQualitativeMorph;
import org.xper.allen.drawing.composition.qualitativemorphs.RadProfileQualitativeMorph;

import javax.vecmath.Vector3d;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class BaseMorphParameters implements ComponentMorphParameters {
    private RadProfileQualitativeMorph radProfileMorph;
    private CurvatureRotationQualitativeMorph curvatureRotationMorph;
    private LengthMetricMorphMagnitude lengthMorph;
    private MetricMorphOrientation orientationMorph;
    private double newRotation;

    //major flags
    boolean doCurvatureRotation = false;
    boolean doRadProfile = true;
    //minor flags
    boolean doLength;
    boolean doOrientation;

    //metric morph params:
    // Metric morph limits
    private final double LENGTH_PERCENT_CHANGE_LOWER = 0.05;
    private final double LENGTH_PERCENT_CHANGE_UPPER = 0.25;
    private final double ORIENTATION_ANGLE_CHANGE_LOWER = 5 * Math.PI / 180;
    private final double ORIENTATION_ANGLE_CHANGE_UPPER = 20 * Math.PI / 180;



    public BaseMorphParameters() {
        distribute();
    }

    private void initializeRadProfileBins() {
        List<Vector3d> radProfileBins = new ArrayList<>();
        double mini = 0.5;
        double fat = 1;
        double tip = 0.0001;
        radProfileBins.add(new Vector3d(fat, fat, fat));
        radProfileBins.add(new Vector3d(mini, mini, fat));
        radProfileBins.add(new Vector3d(mini, fat, mini));
        radProfileBins.add(new Vector3d(fat, mini, mini));
        radProfileBins.add(new Vector3d(mini, fat, fat));
        radProfileBins.add(new Vector3d(fat, mini, fat));
        radProfileBins.add(new Vector3d(fat, fat, mini));
        radProfileBins.add(new Vector3d(fat, mini, tip));
        radProfileBins.add(new Vector3d(fat, fat, tip));
        radProfileBins.add(new Vector3d(mini, fat, tip));
        radProfileMorph.radProfileBins = radProfileBins;
    }

    private void initializeCurvatureBins() {
        List<Bin<Double>> curvatureBins = new ArrayList<>();
        curvatureBins.add(new Bin<>(0.5, 1.0));
        curvatureBins.add(new Bin<>(3.0, 6.0));
        curvatureBins.add(new Bin<>(100000.0, 100000.0001));
        curvatureRotationMorph.curvatureBins = curvatureBins;
    }

    @Override
    public Vector3d morphOrientation(Vector3d oldOrientation) {
        if (!doOrientation) {
            return oldOrientation;
        }
        return orientationMorph.calculateVector();
    }

    @Override
    public Double morphCurvature(Double oldCurvature, AllenMAxisArc arcToMorph) {
        if (!doCurvatureRotation){
            return oldCurvature;

        }
        curvatureRotationMorph.loadParams(oldCurvature, arcToMorph.getTransRotHis_devAngle());
        curvatureRotationMorph.calculate(arcToMorph);
        newRotation = curvatureRotationMorph.getNewRotation();

        return curvatureRotationMorph.getNewCurvature();
    }

    @Override
    public Double morphRotation(Double oldRotation) {
        if (!doCurvatureRotation){
            return oldRotation;
        }
        return newRotation;
    }

    @Override
    public Double morphLength(Double oldLength) {
        if (!doLength) {
            return oldLength;
        }
        return lengthMorph.calculateMagnitude();
    }

    @Override
    public RadiusProfile morphRadius(RadiusProfile oldRadiusProfile) {
        if (!doRadProfile) {
            return oldRadiusProfile;
        }

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

        // Load and calculate new radii
        radProfileMorph.loadParams(junctionInfo.getRadius(), midpointInfo.getRadius(), endpointInfo.getRadius());
        radProfileMorph.calculate();

        // Create new radius profile
        RadiusProfile newRadiusProfile = new RadiusProfile();
        newRadiusProfile.addRadiusInfo(junctionInfo.getuNdx(),
                new RadiusInfo(radProfileMorph.getNewJunc(), junctionInfo.getuNdx(), RADIUS_TYPE.JUNCTION, false));
        newRadiusProfile.addRadiusInfo(midpointInfo.getuNdx(),
                new RadiusInfo(radProfileMorph.getNewMid(), midpointInfo.getuNdx(), RADIUS_TYPE.MIDPT, false));
        newRadiusProfile.addRadiusInfo(endpointInfo.getuNdx(),
                new RadiusInfo(radProfileMorph.getNewEnd(), endpointInfo.getuNdx(), RADIUS_TYPE.ENDPT, false));

        return newRadiusProfile;
    }

    @Override
    public void distribute() {
        radProfileMorph = new RadProfileQualitativeMorph(1, 2,
                false);
        curvatureRotationMorph = new CurvatureRotationQualitativeMorph();
        initializeRadProfileBins();
        initializeCurvatureBins();

        // Implement the desired probability distribution
        double random = Math.random();
        if (random < 1.0 / 3.0) {
            // Only curvatureRotation
            doCurvatureRotation = true;
            doRadProfile = false;
        } else if (random < 2.0 / 3.0) {
            // Only radProfile
            doCurvatureRotation = false;
            doRadProfile = true;
        } else {
            // Both curvatureRotation and radProfile
            doCurvatureRotation = true;
            doRadProfile = true;
        }

        // Distribute minor morphs
        doLength = Math.random() < 0.5; // Length can be true in any case
        doOrientation = doCurvatureRotation; // Orientation only if curvatureRotation is true

        // Initialize metric morph parameters
        if (doLength) {
            lengthMorph.percentChangeLowerBound = LENGTH_PERCENT_CHANGE_LOWER;
            lengthMorph.percentChangeUpperBound = LENGTH_PERCENT_CHANGE_UPPER;
        }
        if (doOrientation) {
            orientationMorph.setAngleChangeLowerBound(ORIENTATION_ANGLE_CHANGE_LOWER);
            orientationMorph.setAngleChangeUpperBound(ORIENTATION_ANGLE_CHANGE_UPPER);
        }
    }

}