package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.EStimShapeProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;

import static org.xper.allen.pga.RFUtils.checkCompCanFitInRF;

/**
 * Instead of relying on a passed baseMatchStick, this automatically generates a random one.
 */
public class EStimShapeProceduralBehavioralStim extends EStimShapeProceduralStim{


    private ReceptiveField rf;
    private AllenPNGMaker choicePNGMaker;

    public EStimShapeProceduralBehavioralStim(EStimShapeExperimentTrialGenerator generator, ProceduralStimParameters parameters, ReceptiveField rf) {
        super(
                generator,
                parameters,
                null,
                -1,
                false,
                0L, 0);
        this.rf = rf;
    }


    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while (true) {
            this.mSticks = new Procedural<>();
            this.mStickSpecs = new Procedural<>();
            System.out.println("Trying to generate EStimShapeProceduralBehavioralStim");
            try {
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
        int maxAttempts = 2;
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
        //Check Random Base Match Stick
        int randLeaf = baseMatchStick.chooseRandLeaf();
        checkCompCanFitInRF(baseMatchStick, rf, randLeaf);


        //Generate Sample
        EStimShapeProceduralMatchStick sample = new EStimShapeProceduralMatchStick(
                rfStrategy,
                rf, generator.getPngMaker().getNoiseMapper()
        );
        sample.setProperties(sampleSizeDegrees, parameters.textureType, 1.0);
        sample.setStimColor(parameters.color);
        baseMatchStick.setMaxAttempts(3);
        sample.genMatchStickFromComponentInNoise(baseMatchStick, randLeaf, 0, true, sample.maxAttempts);

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));
        return sample;

    }

    private ProceduralMatchStick genRandBaseMStick() {
        ProceduralMatchStick baseMStick = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
        baseMStick.setProperties(sampleSizeDegrees, parameters.textureType, 1.0);
        baseMStick.setStimColor(parameters.color);
        baseMStick.genMatchStickRand();

        return baseMStick;
    }

}