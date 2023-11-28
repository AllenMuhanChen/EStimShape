package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.experiment.ExperimentMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;

public class ProceduralRandStim extends ProceduralStim{
    public static final int MAX_TRIES = 50;
    public ProceduralRandStim(ProceduralExperimentBlockGen generator, ProceduralStim.ProceduralStimParameters parameters) {
        super(generator, parameters, new ProceduralMatchStick(), 0);
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while (true) {
            try {
                mSticks = new Procedural<>();
                baseMatchStick = genRandBaseMStick();
                baseMatchStick.setMaxAttempts(MAX_TRIES);
                drivingComponent = baseMatchStick.chooseRandLeaf();
                System.out.println("Driving Component: " + drivingComponent);
                generateNonBaseMatchSticksAndSaveSpecs();
                break;
            } catch (ExperimentMatchStick.MorphRepetitionException me) {
                System.out.println("MorphRepetition FAILED: " + me.getMessage());
            } catch(ExperimentMatchStick.MorphException me) {
                System.out.println("Morph EXCEPTION: " + me.getMessage());
            } catch (Exception e) {
                System.out.println("EXCEPTION: " + e.getMessage());
            }
        }

    }

    protected void generateNonBaseMatchSticksAndSaveSpecs() {
        //Generate Sample
        ProceduralMatchStick sample = new ProceduralMatchStick();
        sample.setProperties(generator.getMaxImageDimensionDegrees());
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromDrivingComponent(baseMatchStick, drivingComponent);
        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample, stimObjIds.getSample()));

        //Generate Match
        mSticks.setMatch(sample);
        mStickSpecs.setMatch(mStickToSpec(sample, stimObjIds.getMatch()));

        for (int i = 0; i < numProceduralDistractors; i++) {
            ProceduralMatchStick proceduralDistractor = new ProceduralMatchStick();
            proceduralDistractor.setProperties(generator.getMaxImageDimensionDegrees());
            proceduralDistractor.setStimColor(parameters.color);
            proceduralDistractor.genNewDrivingComponentMatchStick(sample, parameters.morphMagnitude);
            mSticks.proceduralDistractors.add(proceduralDistractor);
            mStickSpecs.proceduralDistractors.add(mStickToSpec(proceduralDistractor, stimObjIds.proceduralDistractors.get(i)));
        }

        //Generate Rand Distractors
        for (int i = 0; i<numRandDistractors; i++) {
            ProceduralMatchStick randDistractor = new ProceduralMatchStick();
            randDistractor.setProperties(generator.getMaxImageDimensionDegrees());
            randDistractor.setStimColor(parameters.color);
            randDistractor.genMatchStickRand();
            mSticks.randDistractors.add(randDistractor);
            mStickSpecs.randDistractors.add(mStickToSpec(randDistractor, stimObjIds.randDistractors.get(i)));
        }
    }

    private ProceduralMatchStick genRandBaseMStick() {
        ProceduralMatchStick baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(generator.getMaxImageDimensionDegrees());
        baseMStick.setStimColor(parameters.color);
        baseMStick.genMatchStickRand();
        return baseMStick;
    }
}