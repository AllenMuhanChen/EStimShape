package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;

public class EStimShapeTwoByTwoBehavioralStim extends EStimShapeTwoByTwoStim {
    private ReceptiveField rf;

    public EStimShapeTwoByTwoBehavioralStim(EStimExperimentTrialGenerator generator, ProceduralStimParameters parameters, ReceptiveField rf, int nComp) {
        super(generator, parameters, null, -1,
            false, nComp);
        this.rf = rf;
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while(true) {
            this.mSticks = new Procedural<>();
            this.mStickSpecs = new Procedural<>();
            System.out.println("Trying to generate EStimShapeTwoByTwoBehavioralStim");
            try {
                baseMatchStick = genRandBaseMStick();
                baseDrivingComponent = baseMatchStick.chooseRandLeaf();
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
                rf
        );
        sample.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, ((EStimExperimentTrialGenerator) generator).getRfSource()), parameters.textureType);
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromComponentInNoise(baseMatchStick, baseDrivingComponent, this.nComp, false);

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));
        return sample;

    }

    private ProceduralMatchStick genRandBaseMStick() {
        ProceduralMatchStick baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(parameters.getSize(), "SHADE");
        baseMStick.setStimColor(parameters.color);
        baseMStick.genMatchStickRand();
        return baseMStick;
    }

    @Override
    public RewardBehavior specifyRewardBehavior() {
        return RewardBehaviors.rewardMatchOnly();
    }

}