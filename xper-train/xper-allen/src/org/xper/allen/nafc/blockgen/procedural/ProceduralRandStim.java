package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.util.AllenDbUtil;

public class ProceduralRandStim extends ProceduralStim{
    public static final int MAX_TRIES = 10;

    public ProceduralRandStim(NAFCBlockGen generator, ProceduralStim.ProceduralStimParameters parameters) {
        super(generator, parameters, new ProceduralMatchStick(), 0);
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while (true) {
            try {
                mSticks = new Procedural<>();
                baseMatchStick = genRandBaseMStick();
                baseMatchStick.setMaxAttempts(MAX_TRIES);
                System.out.println("Driving Component: " + morphComponentIndex);
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
        //Generate Sample
        ProceduralMatchStick sample = new ProceduralMatchStick();
        sample.setProperties(parameters.getSize(), "SHADE");
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromComponentInNoise(baseMatchStick, baseMatchStick.chooseRandLeaf(), 0);

        noiseComponentIndex = sample.getDrivingComponent();
        morphComponentIndex = sample.getDrivingComponent();

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample, stimObjIds.getSample()));

        //Generate Match
        ProceduralMatchStick match = new ProceduralMatchStick();
        match.setProperties(parameters.getSize(), "SHADE");
        match.setStimColor(parameters.color);
        match.genNewComponentMatchStick(sample, morphComponentIndex, noiseComponentIndex, 0.1, 0.5);
        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match, stimObjIds.getMatch()));

        for (int i = 0; i < numProceduralDistractors; i++) {
            ProceduralMatchStick proceduralDistractor = new ProceduralMatchStick();
            proceduralDistractor.setProperties(parameters.getSize(), "SHADE");
            proceduralDistractor.setStimColor(parameters.color);
            proceduralDistractor.genNewComponentMatchStick(sample, morphComponentIndex, noiseComponentIndex, parameters.morphMagnitude, 0.5);
            mSticks.proceduralDistractors.add(proceduralDistractor);
            mStickSpecs.proceduralDistractors.add(mStickToSpec(proceduralDistractor, stimObjIds.proceduralDistractors.get(i)));
        }

        //Generate Rand Distractors
        for (int i = 0; i<numRandDistractors; i++) {
            ProceduralMatchStick randDistractor = new ProceduralMatchStick();
            randDistractor.setProperties(parameters.getSize(), "SHADE");
            randDistractor.setStimColor(parameters.color);
            randDistractor.genMatchStickRand();
            mSticks.randDistractors.add(randDistractor);
            mStickSpecs.randDistractors.add(mStickToSpec(randDistractor, stimObjIds.randDistractors.get(i)));
        }
    }

    private ProceduralMatchStick genRandBaseMStick() {
        ProceduralMatchStick baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(parameters.getSize(), "SHADE");
        baseMStick.setStimColor(parameters.color);
        baseMStick.genMatchStickRand();
        return baseMStick;
    }

    @Override
    protected void writeStimSpec(){
        NAFCStimSpecWriter stimSpecWriter = new NAFCStimSpecWriter(
                new ProceduralRandGenType(generator).getLabel(),
                getStimId(),
                (AllenDbUtil) generator.getDbUtil(),
                parameters,
                coords,
                parameters.numChoices,
                stimObjIds, RewardPolicy.LIST, new int[]{0});

        stimSpecWriter.writeStimSpec();

    }
}