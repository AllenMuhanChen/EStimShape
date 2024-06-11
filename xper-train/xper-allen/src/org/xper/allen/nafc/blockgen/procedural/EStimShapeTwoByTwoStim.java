package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.procedural.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.TwobyTwoMatchStick;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.time.TimeUtil;

import java.util.LinkedList;
import java.util.List;

public class EStimShapeTwoByTwoStim extends EStimShapeProceduralStim{
    protected int baseDrivingComponent;

    public EStimShapeTwoByTwoStim(EStimExperimentTrialGenerator generator, ProceduralStimParameters parameters, ProceduralMatchStick baseMatchStick, int morphComponentIndex, boolean isEStimEnabled) {
        super(generator, parameters, baseMatchStick, morphComponentIndex, isEStimEnabled);
        this.baseDrivingComponent = morphComponentIndex;
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while(true) {
            this.mSticks = new Procedural<>();
            this.mStickSpecs = new Procedural<>();
            System.out.println("Trying to generate EStimShapeProceduralStim");
            try {
                EStimShapeTwoByTwoMatchStick sample = (EStimShapeTwoByTwoMatchStick) generateSample();

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
        swappedBaseMStick.genMorphedBaseMatchStick(match, morphComponentIndex, false, 100);
        mSticks.proceduralDistractors.add(swappedBaseMStick);
        mStickSpecs.proceduralDistractors.add(mStickToSpec(swappedBaseMStick, stimObjIds.proceduralDistractors.get(0)));

        TwobyTwoMatchStick swappedInNoiseMStick = new TwobyTwoMatchStick();
        correctNoiseRadius(swappedInNoiseMStick);
        swappedInNoiseMStick.setProperties(parameters.getSize(), parameters.textureType);
        swappedInNoiseMStick.setStimColor(parameters.color);
        swappedInNoiseMStick.genMorphedDrivingComponentMatchStick(match, 0.7, 0.5,
                false);
        mSticks.proceduralDistractors.add(swappedInNoiseMStick);
        mStickSpecs.proceduralDistractors.add(mStickToSpec(swappedInNoiseMStick, stimObjIds.proceduralDistractors.get(1)));

        TwobyTwoMatchStick swappedBothMStick = new TwobyTwoMatchStick();
        correctNoiseRadius(swappedBothMStick);
        swappedBothMStick.setProperties(parameters.getSize(), parameters.textureType);
        swappedBothMStick.setStimColor(parameters.color);
        swappedBothMStick.genSwappedBaseAndDrivingComponentMatchStick(swappedBaseMStick,
                morphComponentIndex,
                swappedInNoiseMStick, false);
        mSticks.proceduralDistractors.add(swappedBothMStick);
        mStickSpecs.proceduralDistractors.add(mStickToSpec(swappedBothMStick, stimObjIds.proceduralDistractors.get(2)));
    }

    @Override
    protected ProceduralMatchStick generateSample() {
        int nComp = (int) Math.round(Math.random()) + 1;
        //Generate Sample
        EStimShapeTwoByTwoMatchStick sample = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                ((EStimExperimentTrialGenerator) generator).getRF()
        );
        sample.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, ((EStimExperimentTrialGenerator) generator).getRfSource()), parameters.textureType);
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromComponentInNoise(baseMatchStick, baseDrivingComponent, nComp, true);

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample, stimObjIds.getSample()));
        return sample;

    }

    @Override
    protected void generateMatch(ProceduralMatchStick sample) {
        TwobyTwoMatchStick match = new TwobyTwoMatchStick();
        match.setProperties(parameters.getSize(), parameters.textureType);
        match.setStimColor(parameters.color);
        match.genMatchStickFromShapeSpec(mStickSpecs.getSample(), new double[]{0,0,0});
        match.centerShape();

        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match, stimObjIds.getMatch()));
    }



}