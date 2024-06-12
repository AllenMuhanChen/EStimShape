package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.procedural.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;

public class EStimShapeTwoByTwoBehavioralStim extends EStimShapeTwoByTwoStim{
    private ReceptiveField rf;
    private int nComp;

    public EStimShapeTwoByTwoBehavioralStim(EStimExperimentTrialGenerator generator, ProceduralStimParameters parameters, ReceptiveField rf) {
        super(generator, parameters, null, -1, false);
        this.rf = rf;
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        nComp = (int) Math.round(Math.random()+2);
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
        sample.genMatchStickFromComponentInNoise(baseMatchStick, baseDrivingComponent, nComp, false);

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample, stimObjIds.getSample()));
        return sample;

    }

    private ProceduralMatchStick genRandBaseMStick() {
        ProceduralMatchStick baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, ((EStimExperimentTrialGenerator) generator).getRfSource()), "SHADE");
        baseMStick.setStimColor(parameters.color);
        baseMStick.genMatchStickRand();
        return baseMStick;
    }
}