package org.xper.allen.nafc.blockgen.procedural;

import org.xper.Dependency;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.NAFCStim;

import javax.swing.*;
import java.util.LinkedList;
import java.util.List;

public class EStimExperimentGenType extends ProceduralRandGenType<EStimExperimentGenType.EStimExperimentGenParameters> {

    @Dependency
    String gaSpecPath;

    protected JTextField numDeltaTrialSetsField;
    protected JTextField stimIdField;
    protected JTextField compIdField;

    public EStimExperimentGenType() {
        super();
    }

    public String getLabel() {
        return "EStimExperiment";
    }

    public EStimExperimentGenParameters readFromFields() {
        int numDeltaTrialSets = Integer.parseInt(numDeltaTrialSetsField.getText());
        long stimId = Long.parseLong(stimIdField.getText());
        int compId = Integer.parseInt(compIdField.getText());
        EStimExperimentGenParameters params = new EStimExperimentGenParameters(super.readFromFields(), numDeltaTrialSets, stimId, compId);
        return params;
    }

    @Override
    protected List<NAFCStim> genTrials(EStimExperimentGenParameters parameters) {
        List<NAFCStim> newBlock = new LinkedList<>();


        int morphIndex = parameters.compId;
        int noiseIndex = morphIndex;

        //use that trial's base matchstick to generate the rest of the trials
        for (int i = 0; i < parameters.getNumTrials(); i++) {
            //Generate the base matchstick
            ProceduralMatchStick baseMStick = new ProceduralMatchStick(generator.getPngMaker().getNoiseMapper());
            baseMStick.setProperties(generator.getImageDimensionsDegrees(), "SHADE");
            baseMStick.setStimColor(parameters.getProceduralStimParameters().color);
            baseMStick.genMatchStickFromFile(gaSpecPath + "/" + parameters.stimId + "_spec.xml");

            //using estim values set on the IntanGUI
            EStimShapeProceduralStim stim = new EStimShapeProceduralStim((EStimShapeExperimentTrialGenerator) generator, parameters.getProceduralStimParameters(), baseMStick, morphIndex, true);
            newBlock.add(stim);
        }

        //ADD DELTA TRIALS
        //choose random trials to make delta trials from
        List<ProceduralStim> deltaTrials = new LinkedList<>();
        for (int i=0; i<parameters.numDeltaTrialSets; i++){
            int randIndex = (int) (Math.random() * parameters.getNumTrials());
            ProceduralStim baseStim = (ProceduralStim) newBlock.get(randIndex);
            ProceduralStim deltaMorph = new DeltaStim(baseStim, true, false);
            ProceduralStim deltaNoise = new DeltaStim(baseStim, false, true);
            ProceduralStim deltaBoth = new DeltaStim(baseStim, true, true);
            deltaTrials.add(deltaMorph);
            deltaTrials.add(deltaNoise);
            deltaTrials.add(deltaBoth);
        }
        newBlock.addAll(deltaTrials);
        return newBlock;
    }

    public void initFields() {
        super.initFields();
        numDeltaTrialSetsField = new JTextField("3", 10);
        stimIdField = new JTextField("0", 10);
        compIdField = new JTextField("0", 10);
        labelsForFields.put(numDeltaTrialSetsField, "numDeltaTrialSets:");
        defaultsForFields.put(numDeltaTrialSetsField, "3");
        labelsForFields.put(stimIdField, "stimId:");
        defaultsForFields.put(stimIdField, "0");
        labelsForFields.put(compIdField, "compId:");
        defaultsForFields.put(compIdField, "0");
    }

    @Override
    public void loadParametersIntoFields(GenParameters blockParams) {

        super.loadParametersIntoFields(blockParams);
        numDeltaTrialSetsField.setText(String.valueOf(((EStimExperimentGenParameters) blockParams).numDeltaTrialSets));
        stimIdField.setText(String.valueOf(((EStimExperimentGenParameters) blockParams).stimId));
        compIdField.setText(String.valueOf(((EStimExperimentGenParameters) blockParams).compId));
    }

    public void setGaSpecPath(String gaSpecPath) {
        this.gaSpecPath = gaSpecPath;
    }

    public static class EStimExperimentGenParameters extends MockExperimentGenType.MockExperimentGenParameters {
        public long stimId;
        public int compId;

        public EStimExperimentGenParameters(GenParameters genParameters, int numDeltaTrialSets, long stimId, int compId) {
            super(genParameters, numDeltaTrialSets);
            this.stimId = stimId;
            this.compId = compId;
        }

        public EStimExperimentGenParameters() {
        }
    }
}