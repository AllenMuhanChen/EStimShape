package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.procedural.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.experiment.EStimShapeProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.TwobyTwoMatchStick;
import org.xper.time.TimeUtil;

import javax.vecmath.Point3d;
import java.util.LinkedList;
import java.util.List;

public class EStimShapeTwoByTwoStim extends EStimShapeProceduralStim{
    public EStimShapeTwoByTwoStim(EStimExperimentTrialGenerator generator, ProceduralStimParameters parameters, ProceduralMatchStick baseMatchStick, int morphComponentIndex, boolean isEStimEnabled) {
        super(generator, parameters, baseMatchStick, morphComponentIndex, isEStimEnabled);
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while(true) {
            System.out.println("Trying to generate EStimShapeProceduralStim");
            try {
                EStimShapeProceduralMatchStick sample = (EStimShapeProceduralMatchStick) generateSample();

                morphComponentIndex = sample.getDrivingComponent();
                noiseComponentIndex = sample.getDrivingComponent();

                generateMatch(sample);

                generateProceduralDistractors(mSticks.getMatch());

                break;
            } catch (Exception e) {
                System.out.println("MorphRepetition FAILED: " + e.getMessage());
            }
        }
    }

    @Override
    protected void assignStimObjIds() {
        TimeUtil timeUtil = generator.getGlobalTimeUtil();
        long sampleId = timeUtil.currentTimeMicros();
        long matchId = sampleId + 1;
        numProceduralDistractors = 3;
        numRandDistractors = 0;
        List<Long> proceduralDistractorIds = new LinkedList<>();
        for (int i = 0; i < numProceduralDistractors; i++) {
            proceduralDistractorIds.add(matchId + i + 1);
        }
        List<Long> randDistractorIds = new LinkedList<>();
        for (int i = 0; i < numRandDistractors; i++) {
            randDistractorIds.add(matchId + i + 1 + numProceduralDistractors);
        }
        stimObjIds = new Procedural<Long>(sampleId, matchId, proceduralDistractorIds, randDistractorIds);
    }

    @Override
    protected void generateProceduralDistractors(ProceduralMatchStick match) {
        TwobyTwoMatchStick swappedBaseMStick = new TwobyTwoMatchStick();
        correctNoiseRadius(swappedBaseMStick);
        swappedBaseMStick.setProperties(parameters.getSize(), parameters.textureType);
        swappedBaseMStick.setStimColor(parameters.color);
        swappedBaseMStick.genNewBaseMatchStick(match, morphComponentIndex, false, 100);
        mSticks.proceduralDistractors.add(swappedBaseMStick);
        mStickSpecs.proceduralDistractors.add(mStickToSpec(swappedBaseMStick, stimObjIds.proceduralDistractors.get(0)));

        TwobyTwoMatchStick swappedInNoiseMStick = new TwobyTwoMatchStick();
        correctNoiseRadius(swappedInNoiseMStick);
        swappedInNoiseMStick.setProperties(parameters.getSize(), parameters.textureType);
        swappedInNoiseMStick.setStimColor(parameters.color);
        swappedInNoiseMStick.genNewDrivingComponentMatchStick(match, 0.5, 0.5, false);
        mSticks.proceduralDistractors.add(swappedInNoiseMStick);
        mStickSpecs.proceduralDistractors.add(mStickToSpec(swappedInNoiseMStick, stimObjIds.proceduralDistractors.get(1)));

        TwobyTwoMatchStick swappedBothMStick = new TwobyTwoMatchStick();
        correctNoiseRadius(swappedBothMStick);
        swappedBothMStick.setProperties(parameters.getSize(), parameters.textureType);
        swappedBothMStick.setStimColor(parameters.color);
        swappedBothMStick.genSwappedBaseAndDrivingComponentMatchStick(swappedBaseMStick,morphComponentIndex, swappedInNoiseMStick, false);
        mSticks.proceduralDistractors.add(swappedBothMStick);
        mStickSpecs.proceduralDistractors.add(mStickToSpec(swappedBothMStick, stimObjIds.proceduralDistractors.get(2)));
    }

    @Override
    protected void generateMatch(ProceduralMatchStick sample) {
        TwobyTwoMatchStick match = new TwobyTwoMatchStick();
        match.setProperties(parameters.getSize(), parameters.textureType);
        match.setStimColor(parameters.color);
        match.genMatchStickFromShapeSpec(mStickSpecs.getSample(), new double[]{0,0,0});
        match.moveCenterOfMassTo(new Point3d(0,0,0));


        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match, stimObjIds.getMatch()));
    }



}