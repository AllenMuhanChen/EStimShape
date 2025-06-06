package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.TwoByTwoMatchStick;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.time.TimeUtil;

import java.util.LinkedList;
import java.util.List;

public class EStimShapeTwoByTwoStim extends EStimShapeProceduralStim{
    protected int baseDrivingComponent;
    protected int nComp;

    public EStimShapeTwoByTwoStim(EStimShapeExperimentTrialGenerator generator,
                                  ProceduralStimParameters parameters,
                                  ProceduralMatchStick baseMatchStick,
                                  int morphComponentIndex,
                                  boolean isEStimEnabled,
                                  int nComp) {
        super(generator, parameters, baseMatchStick, morphComponentIndex, isEStimEnabled);
        this.baseDrivingComponent = morphComponentIndex;
        if (nComp == 0){
            this.nComp = (int) Math.round(Math.random()+2);
        }
        else{
            this.nComp = nComp;
        }
        this.numProceduralDistractors = parameters.numChoices - numRandDistractors - 1;
        this.numRandDistractors = 0;
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
        System.out.println(numProceduralDistractors);
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
        TwoByTwoMatchStick swappedBaseMStick = new TwoByTwoMatchStick(generator.getPngMaker().getNoiseMapper());
        if (numProceduralDistractors >= 1) {
            correctNoiseRadius(swappedBaseMStick);
            swappedBaseMStick.setProperties(parameters.getSize(), parameters.textureType, 1.0);
            swappedBaseMStick.setStimColor(parameters.color);
            swappedBaseMStick.genMorphedBaseMatchStick(match,
                    morphComponentIndex,
                    30,
                    false,
                    true);
            mSticks.addProceduralDistractor(swappedBaseMStick);
            mStickSpecs.addProceduralDistractor(mStickToSpec(swappedBaseMStick));
        }

        TwoByTwoMatchStick swappedInNoiseMStick = new TwoByTwoMatchStick(generator.getPngMaker().getNoiseMapper());
        if (numProceduralDistractors >= 2) {
            correctNoiseRadius(swappedInNoiseMStick);
            swappedInNoiseMStick.setProperties(parameters.getSize(), parameters.textureType, 1.0);
            swappedInNoiseMStick.setStimColor(parameters.color);
            swappedInNoiseMStick.genMorphedDrivingComponentMatchStick(match,
                    0.7, 1.0/3.0,
                    false, true, 30);
            mSticks.addProceduralDistractor(swappedInNoiseMStick);
            mStickSpecs.addProceduralDistractor(mStickToSpec(swappedInNoiseMStick));
        }

        TwoByTwoMatchStick swappedBothMStick = new TwoByTwoMatchStick(generator.getPngMaker().getNoiseMapper());
        if (numProceduralDistractors >= 3) {
            correctNoiseRadius(swappedBothMStick);
            swappedBothMStick.setProperties(parameters.getSize(), parameters.textureType, 1.0);
            swappedBothMStick.setStimColor(parameters.color);
            swappedBothMStick.genSwappedBaseAndDrivingComponentMatchStick(swappedBaseMStick,
                    morphComponentIndex,
                    swappedInNoiseMStick, false, 15);
            mSticks.addProceduralDistractor(swappedBothMStick);
            mStickSpecs.addProceduralDistractor(mStickToSpec(swappedBothMStick));
        }
    }

    @Override
    protected ProceduralMatchStick generateSample() {

        //Generate Sample
        EStimShapeTwoByTwoMatchStick sample = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                ((EStimShapeExperimentTrialGenerator) generator).getRF(),
                null);
        sample.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE,
                ((EStimShapeExperimentTrialGenerator) generator).getRfSource().getRFRadiusDegrees()), parameters.textureType, 1.0);
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromComponentInNoise(baseMatchStick, baseDrivingComponent, nComp,
                true, 15, generator.getPngMaker().getNoiseMapper());

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));
        return sample;

    }

    @Override
    protected void generateMatch(ProceduralMatchStick sample) {
        TwoByTwoMatchStick match = new TwoByTwoMatchStick(generator.getPngMaker().getNoiseMapper());
        match.setProperties(parameters.getSize(), parameters.textureType, 1.0);
        match.setStimColor(parameters.color);
        match.genMatchStickFromShapeSpec(mStickSpecs.getSample(), new double[]{0,0,0});
        match.centerShape();
//        match.checkMStickSize();

        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match));
    }


    @Override
    public RewardBehavior specifyRewardBehavior() {
        if (isEStimEnabled) {
            return RewardBehaviors.rewardAnyChoice();
        } else{
            return RewardBehaviors.rewardMatchOnly();
        }

    }

}