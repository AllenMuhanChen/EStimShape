package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.blockgen.psychometric.NAFCStimSpecWriter;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.util.AllenDbUtil;

public class ProceduralRandStim extends ProceduralStim{
    public static final int MAX_TRIES = 10;

    public ProceduralRandStim(NAFCBlockGen generator, ProceduralStim.ProceduralStimParameters parameters) {
        super(generator, parameters, new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper()), 0);
    }

    @Override
    protected void generateMatchSticksAndSaveSpecs() {
        while (true) {
            this.mSticks = new Procedural<>();
            this.mStickSpecs = new Procedural<>();
            try {
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
        ProceduralMatchStick sample = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
        sample.setProperties(parameters.getSize(), "SHADE");
        sample.setStimColor(parameters.color);
        sample.genMatchStickFromComponentInNoise(baseMatchStick, baseMatchStick.chooseRandLeaf(), 0, true, sample.maxAttempts, generator.getPngMaker().getNoiseMapper());

        noiseComponentIndex = sample.getDrivingComponent();
        morphComponentIndex = sample.getDrivingComponent();

        mSticks.setSample(sample);
        mStickSpecs.setSample(mStickToSpec(sample));

        //Generate Match
        ProceduralMatchStick match = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
        match.setProperties(parameters.getSize(), "SHADE");
        match.setStimColor(parameters.color);
        match.genNewComponentMatchStick(sample, morphComponentIndex, 0.1, 0.5, true, match.maxAttempts);
        mSticks.setMatch(match);
        mStickSpecs.setMatch(mStickToSpec(match));

        for (int i = 0; i < numProceduralDistractors; i++) {
            ProceduralMatchStick proceduralDistractor = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
            proceduralDistractor.setProperties(parameters.getSize(), "SHADE");
            proceduralDistractor.setStimColor(parameters.color);
            proceduralDistractor.genNewComponentMatchStick(sample, morphComponentIndex, parameters.morphMagnitude, 0.5, true, proceduralDistractor.maxAttempts);
            mSticks.addProceduralDistractor(proceduralDistractor);
            mStickSpecs.addProceduralDistractor(mStickToSpec(proceduralDistractor));
        }

        //Generate Rand Distractors
        for (int i = 0; i<numRandDistractors; i++) {
            ProceduralMatchStick randDistractor = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
            randDistractor.setProperties(parameters.getSize(), "SHADE");
            randDistractor.setStimColor(parameters.color);
            randDistractor.genMatchStickRand();
            mSticks.addRandDistractor(randDistractor);
            mStickSpecs.addRandDistractor(mStickToSpec(randDistractor));
        }
    }

    private ProceduralMatchStick genRandBaseMStick() {
        ProceduralMatchStick baseMStick = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
        baseMStick.setProperties(parameters.getSize(), "SHADE");
        baseMStick.setStimColor(parameters.color);
        baseMStick.genMatchStickRand();
        return baseMStick;
    }

    @Override
    protected void writeStimSpec(){
        NAFCStimSpecWriter stimSpecWriter = NAFCStimSpecWriter.createForNoEStim(
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