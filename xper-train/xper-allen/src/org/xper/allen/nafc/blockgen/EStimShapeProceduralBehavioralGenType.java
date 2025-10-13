package org.xper.allen.nafc.blockgen;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.procedural.EStimShapeProceduralBehavioralStim;
import org.xper.allen.nafc.blockgen.procedural.GenParameters;
import org.xper.allen.nafc.blockgen.procedural.ProceduralRandGenType;

import java.util.LinkedList;
import java.util.List;

public class EStimShapeProceduralBehavioralGenType extends ProceduralRandGenType<GenParameters> {

    public EStimShapeProceduralBehavioralGenType() {
        super();
    }

    @Override
    public String getLabel() {
        return "EStimBehavioral";
    }

    @Override
    protected List<NAFCStim> genTrials(GenParameters genParameters) {
        List<NAFCStim> newBlock = new LinkedList<>();

        // Cast generator to access RF functionality
//        if (!(generator instanceof EStimShapeExperimentTrialGenerator)) {
//            throw new IllegalStateException("EStimBehavioral requires EStimShapeExperimentTrialGenerator");
//        }
        EStimShapeExperimentTrialGenerator estimGen = (EStimShapeExperimentTrialGenerator) generator;

        // Get the real RF from the generator
        ReceptiveField realRF = estimGen.getRF();

        // Generate behavioral trials, all using the real RF
        for (int i = 0; i < genParameters.getNumTrials(); i++) {
            EStimShapeProceduralBehavioralStim stim = new EStimShapeProceduralBehavioralStim(
                    estimGen,
                    genParameters.getProceduralStimParameters(),
                    realRF
            );
            newBlock.add(stim);
        }

        return newBlock;
    }

    @Override
    public String getInfo() {
        return "Type: " + getLabel() +
                ", Trials: " + getNumTrials() +
                ", NoiseChance: " + noiseChanceField.getText() +
                ", NumChoices: " + numChoicesField.getText() +
                ", NumRandDistractors: " + numRandDistractorsField.getText();
    }
}