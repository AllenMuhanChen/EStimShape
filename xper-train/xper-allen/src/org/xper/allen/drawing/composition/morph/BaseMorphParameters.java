package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.qualitativemorphs.Bin;
import org.xper.allen.drawing.composition.qualitativemorphs.CurvatureRotationQualitativeMorph;
import org.xper.allen.drawing.composition.qualitativemorphs.RadProfileQualitativeMorph;

import javax.vecmath.Vector3d;
import java.util.ArrayList;
import java.util.List;

public class BaseMorphParameters implements ComponentMorphParameters {
    private RadProfileQualitativeMorph radProfileMorph;
    private CurvatureRotationQualitativeMorph curvatureRotationMorph;
    private double newRotation;

    public BaseMorphParameters() {
        radProfileMorph = new RadProfileQualitativeMorph(1, 2, false);
        curvatureRotationMorph = new CurvatureRotationQualitativeMorph();
        initializeRadProfileBins();
        initializeCurvatureBins();
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
        // To be implemented
        return oldOrientation;
    }

    @Override
    public Double morphCurvature(Double oldCurvature, AllenMAxisArc arcToMorph) {
        curvatureRotationMorph.loadParams(oldCurvature, arcToMorph.getTransRotHis_devAngle());
        curvatureRotationMorph.calculate(arcToMorph);
        newRotation = curvatureRotationMorph.getNewRotation();

        return curvatureRotationMorph.getNewCurvature();
    }

    @Override
    public Double morphRotation(Double oldRotation) {
        return newRotation;
    }

    @Override
    public Double morphLength(Double oldLength) {
        // To be implemented
        return oldLength;
    }

    @Override
    public RadiusProfile morphRadius(RadiusProfile oldRadiusProfile) {
        Vector3d oldRadProfile = new Vector3d(
                oldRadiusProfile.getRadiusInfo(1).getRadius(),
                oldRadiusProfile.getRadiusInfo(26).getRadius(),
                oldRadiusProfile.getRadiusInfo(51).getRadius()
        );
        radProfileMorph.loadParams(oldRadProfile.x, oldRadProfile.y, oldRadProfile.z);
        radProfileMorph.calculate();

        RadiusProfile newRadiusProfile = new RadiusProfile();
        newRadiusProfile.addRadiusInfo(1, new RadiusInfo(radProfileMorph.getNewJunc(), 1, NormalDistributedComponentMorphParameters.RADIUS_TYPE.JUNCTION, false));
        newRadiusProfile.addRadiusInfo(26, new RadiusInfo(radProfileMorph.getNewMid(), 26, NormalDistributedComponentMorphParameters.RADIUS_TYPE.MIDPT, false));
        newRadiusProfile.addRadiusInfo(51, new RadiusInfo(radProfileMorph.getNewEnd(), 51, NormalDistributedComponentMorphParameters.RADIUS_TYPE.ENDPT, false));

        return newRadiusProfile;
    }

    @Override
    public void redistribute() {
        // No redistribution needed for this implementation
    }
}