package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.experiment.ExperimentMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;

public class ProceduralRandStim extends ProceduralStim{
    public static final int MAX_TRIES = 10;
    private int nComp;

    public ProceduralRandStim(NAFCBlockGen generator, ProceduralStim.ProceduralStimParameters parameters) {
        super(generator, parameters, new ProceduralMatchStick(), 0, 0);
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
//        nComp = ProceduralMatchStick.chooseNumComps();
//        System.out.println("NUMBER COMPS: " + nComp);
        while (true) {
            try {
                mSticks = new Procedural<>();
                baseMatchStick = genRandBaseMStick();
                baseMatchStick.setMaxAttempts(MAX_TRIES);
                chooseMorphAndNoiseComponents();
                System.out.println("Driving Component: " + morphComponentIndex);
                generateNonBaseMatchSticksAndSaveSpecs();
                break;
            } catch (ExperimentMatchStick.MorphRepetitionException me) {
                System.err.println("MorphRepetition FAILED: " + me.getMessage());
            } catch(ExperimentMatchStick.MorphException me) {
                System.err.println("Morph EXCEPTION: " + me.getMessage());
            } catch (Exception e) {
                System.err.println("EXCEPTION: " + e.getMessage());
            }
            System.out.println("Starting over from a new base match stick");
        }

    }

    protected void chooseMorphAndNoiseComponents() {
        morphComponentIndex = baseMatchStick.chooseRandLeaf();
        noiseComponentIndex = morphComponentIndex;
    }

    protected void generateNonBaseMatchSticksAndSaveSpecs() {
        //Generate Sample
        ProceduralMatchStick sample = new ProceduralMatchStick();
        sample.setProperties(parameters.getSize());
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromComponent(baseMatchStick, morphComponentIndex, noiseComponentIndex, 0);
        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample, stimObjIds.getSample()));

        //Generate Match
        mSticks.setMatch(sample);
        mStickSpecs.setMatch(mStickToSpec(sample, stimObjIds.getMatch()));

        for (int i = 0; i < numProceduralDistractors; i++) {
            ProceduralMatchStick proceduralDistractor = new ProceduralMatchStick();
            proceduralDistractor.setProperties(parameters.getSize());
            proceduralDistractor.setStimColor(parameters.color);
//            proceduralDistractor.genNewDrivingComponentMatchStick(sample, parameters.morphMagnitude, 0.5);
            proceduralDistractor.genNewComponentMatchStick(sample, morphComponentIndex, noiseComponentIndex, parameters.morphMagnitude, 0.5);
            mSticks.proceduralDistractors.add(proceduralDistractor);
            mStickSpecs.proceduralDistractors.add(mStickToSpec(proceduralDistractor, stimObjIds.proceduralDistractors.get(i)));
        }

        //Generate Rand Distractors
        for (int i = 0; i<numRandDistractors; i++) {
            ProceduralMatchStick randDistractor = new ProceduralMatchStick();
            randDistractor.setProperties(parameters.getSize());
            randDistractor.setStimColor(parameters.color);
            randDistractor.genMatchStickRand();
            mSticks.randDistractors.add(randDistractor);
            mStickSpecs.randDistractors.add(mStickToSpec(randDistractor, stimObjIds.randDistractors.get(i)));
        }
    }

    private ProceduralMatchStick genRandBaseMStick() {
        ProceduralMatchStick baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(parameters.getSize());
        baseMStick.setStimColor(parameters.color);
        baseMStick.genMatchStickRand();
        return baseMStick;
    }

    @Override
    protected void writeStimSpec(){
        NAFCStimSpecWriter stimSpecWriter = new NAFCStimSpecWriter(
                new ProceduralRandGenType(generator).getLabel(),
                getTaskId(),
                generator.getDbUtil(),
                parameters,
                coords,
                parameters.numChoices,
                stimObjIds);

        stimSpecWriter.writeStimSpec();

    }
}