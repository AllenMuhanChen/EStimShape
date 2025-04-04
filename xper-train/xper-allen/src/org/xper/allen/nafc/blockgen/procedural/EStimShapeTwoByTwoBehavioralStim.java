package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;

import java.util.Collections;

public class EStimShapeTwoByTwoBehavioralStim extends EStimShapeTwoByTwoStim {
    private ReceptiveField rf;

    public EStimShapeTwoByTwoBehavioralStim(EStimShapeExperimentTrialGenerator generator, ProceduralStimParameters parameters, ReceptiveField rf, int nComp) {
        super(generator, parameters, null, -1,
            false, nComp);
        this.rf = rf;
        this.nComp = 2;
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while(true) {
            this.mSticks = new Procedural<>();
            this.mStickSpecs = new Procedural<>();
            System.out.println("Trying to generate EStimShapeTwoByTwoBehavioralStim");
            try {
                baseMatchStick = genRandBaseMStick();
                baseDrivingComponent = 1;
                EStimShapeTwoByTwoMatchStick sample = (EStimShapeTwoByTwoMatchStick)
                        generateSample();

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
    protected ProceduralMatchStick generateSample() {
        //Generate Sample
        EStimShapeTwoByTwoMatchStick sample = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                rf,
                null);
        sample.setProperties(
                RFUtils.calculateMStickMaxSizeDiameterDegrees(
                        RFStrategy.PARTIALLY_INSIDE,
                        ((EStimShapeExperimentTrialGenerator) generator).getRfSource().getRFRadiusDegrees()), parameters.textureType, 1.0);
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromComponentInNoise(baseMatchStick, baseDrivingComponent, this.nComp, false, sample.maxAttempts, ((EStimShapeExperimentTrialGenerator) generator).getNoiseMapper());

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));
        return sample;

    }

    private EStimShapeTwoByTwoMatchStick genRandBaseMStick() {
        EStimShapeTwoByTwoMatchStick baseMStick = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                rf, null);
        baseMStick.setProperties(
                RFUtils.calculateMStickMaxSizeDiameterDegrees(
                RFStrategy.PARTIALLY_INSIDE, ((EStimShapeExperimentTrialGenerator) generator).getRfSource().getRFRadiusDegrees()), "SHADE", 1.0);
        baseMStick.setStimColor(parameters.color);
        baseMStick.genMatchStickRand(2);
        baseMStick.setSpecialEndComp(Collections.singletonList(1));
        baseMStick.positionShape();
        return baseMStick;
    }

    @Override
    public RewardBehavior specifyRewardBehavior() {
        return RewardBehaviors.rewardMatchOnly();
    }

}