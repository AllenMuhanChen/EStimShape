package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.procedural.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.experiment.EStimShapeProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;

public class EStimShapeBehavioralStim extends EStimShapeProceduralStim{

    public EStimShapeBehavioralStim(EStimExperimentTrialGenerator generator, ProceduralStimParameters parameters) {
        super(
                generator,
                parameters,
                null,
                -1,
                -1);
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while (true) {
            try {
                mSticks = new Procedural<>();
                baseMatchStick = genRandBaseMStick();
                baseMatchStick.setMaxAttempts(15);
                generateNonBaseMatchSticksAndSaveSpecs();
                break;
            } catch (ProceduralMatchStick.MorphRepetitionException me) {
                System.err.println("MorphRepetition FAILED: " + me.getMessage());
            } catch(ProceduralMatchStick.MorphException me) {
                System.err.println("Morph EXCEPTION: " + me.getMessage());
            } catch (Exception e) {
                System.err.println("EXCEPTION: " + e.getMessage());
            }
            System.out.println("Starting over from a new base match stick");
        }

    }

    protected void generateNonBaseMatchSticksAndSaveSpecs() {
        int nAttempts = 0;
        int maxAttempts = 15;
        while(nAttempts < maxAttempts) {
            nAttempts++;
            try {
                EStimShapeProceduralMatchStick sample = generateSample();

                morphComponentIndex = sample.getDrivingComponent();
                noiseComponentIndex = sample.getDrivingComponent();

                generateMatch(sample);

                generateProceduralDistractors(sample);

                generateRandDistractors();

                break;
            } catch (ProceduralMatchStick.MorphRepetitionException e) {
                System.out.println("MorphRepetition FAILED: " + e.getMessage());
            }
        }
        if (nAttempts == maxAttempts) {
            throw new ProceduralMatchStick.MorphRepetitionException("MorphRepetition FAILED: " + nAttempts + " attempts");
        }
    }

    @Override
    protected EStimShapeProceduralMatchStick generateSample() {

        //Generate Sample
        EStimShapeProceduralMatchStick sample = new EStimShapeProceduralMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                ((EStimExperimentTrialGenerator) generator).getRF()
        );
        sample.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, ((EStimExperimentTrialGenerator) generator).getRfSource()), parameters.textureType);
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromComponentInNoise(baseMatchStick, baseMatchStick.chooseRandLeaf(), 0);

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample, stimObjIds.getSample()));
        return sample;

    }

    private ProceduralMatchStick genRandBaseMStick() {
        ProceduralMatchStick baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(parameters.getSize(), "SHADE");
        baseMStick.setStimColor(parameters.color);
        baseMStick.genMatchStickRand();
        return baseMStick;
    }

}