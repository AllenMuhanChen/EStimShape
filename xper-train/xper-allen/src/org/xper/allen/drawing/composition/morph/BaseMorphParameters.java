package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.metricmorphs.LengthMetricMorphMagnitude;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphOrientation;
import org.xper.allen.drawing.composition.metricmorphs.SizeMetricMorphMagnitude;
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
    private SizeMetricMorphMagnitude thicknessMorph;
    private double newRotation;

    //major flags
    boolean doCurvatureRotation;
    boolean doRadProfile;
    //minor flags
    boolean doLength;
    boolean doOrientation;
    boolean doRadThickness;

    //metric morph params:
    // Metric morph limits
    private final double LENGTH_PERCENT_CHANGE_LOWER = 0.15;
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
        orientationMorph.setOldVector(oldOrientation);
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

        // Apply metric size morphing to thickness if enabled
        double newThickness = originalThickness;
        if (doRadThickness) {
            newThickness = thicknessMorph.calculateMagnitude(originalThickness);
        }

        // Calculate normalized radii
        double normalizedJunc = junctionInfo.getRadius() / originalThickness;
        double normalizedMid = midpointInfo.getRadius() / originalThickness;
        double normalizedEnd = endpointInfo.getRadius() / originalThickness;

        double newNormalizedJunc = normalizedJunc;
        double newNormalizedMid = normalizedMid;
        double newNormalizedEnd = normalizedEnd;

        // Apply radProfile morphing if enabled
        if (doRadProfile) {
            radProfileMorph.loadParams(normalizedJunc, normalizedMid, normalizedEnd);
            radProfileMorph.calculate();
            newNormalizedJunc = radProfileMorph.getNewJunc();
            newNormalizedMid = radProfileMorph.getNewMid();
            newNormalizedEnd = radProfileMorph.getNewEnd();
        }

        // Create new radius profile
        RadiusProfile newRadiusProfile = new RadiusProfile();
        newRadiusProfile.addRadiusInfo(junctionInfo.getuNdx(),
                new RadiusInfo(newNormalizedJunc * originalThickness, junctionInfo.getuNdx(), RADIUS_TYPE.JUNCTION, false));
        newRadiusProfile.addRadiusInfo(midpointInfo.getuNdx(),
                new RadiusInfo(newNormalizedMid * newThickness, midpointInfo.getuNdx(), RADIUS_TYPE.MIDPT, false));
        newRadiusProfile.addRadiusInfo(endpointInfo.getuNdx(),
                new RadiusInfo(newNormalizedEnd * newThickness, endpointInfo.getuNdx(), RADIUS_TYPE.ENDPT, false));

        return newRadiusProfile;
    }

    @Override
    public void distribute() {
        radProfileMorph = new RadProfileQualitativeMorph(1,
                2,
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
        doRadThickness = Math.random() < 0.5; // Thickness can be true in any case
        doOrientation = doCurvatureRotation; // Orientation only if curvatureRotation is true


        // Initialize metric morph parameters
        if (doLength) {
            lengthMorph = new LengthMetricMorphMagnitude(3.5);
            lengthMorph.percentChangeLowerBound = LENGTH_PERCENT_CHANGE_LOWER;
            lengthMorph.percentChangeUpperBound = LENGTH_PERCENT_CHANGE_UPPER;
        }
        if (doOrientation) {
            orientationMorph = new MetricMorphOrientation();
            orientationMorph.setAngleChangeLowerBound(ORIENTATION_ANGLE_CHANGE_LOWER);
            orientationMorph.setAngleChangeUpperBound(ORIENTATION_ANGLE_CHANGE_UPPER);
        }
        if (doRadThickness) {
            thicknessMorph = new SizeMetricMorphMagnitude();
            thicknessMorph.percentChangeLowerBound = 0.19;
            thicknessMorph.percentChangeUpperBound = 0.2;
        }
    }

}