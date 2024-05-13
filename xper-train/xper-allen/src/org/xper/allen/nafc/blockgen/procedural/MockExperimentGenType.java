package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.experiment.EStimShapeProceduralMatchStick;
import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

import javax.swing.*;
import java.util.*;
import java.util.List;

public class MockExperimentGenType extends ProceduralRandGenType<MockExperimentGenType.MockExperimentGenParameters>{

    protected JTextField numDeltaTrialSetsField;

    public MockExperimentGenType(NAFCBlockGen generator) {
        super(generator);
    }

    public String getLabel() {
        return "MockExperiment";
    }


    public MockExperimentGenParameters readFromFields() {
        int numDeltaTrialSets = Integer.parseInt(numDeltaTrialSetsField.getText());
        MockExperimentGenParameters params = new MockExperimentGenParameters(super.readFromFields(), numDeltaTrialSets);
        return params;
    }

    @Override
    protected List<NAFCStim> genTrials(MockExperimentGenParameters parameters) {
        List<NAFCStim> newBlock = new LinkedList<>();

        //Generate the base matchstick
        EStimShapeProceduralMatchStick baseMStick = new EStimShapeProceduralMatchStick();
        baseMStick.setProperties(generator.getImageDimensionsDegrees(), "SHADE");
        baseMStick.setStimColor(parameters.getProceduralStimParameters().color);
        baseMStick.genMatchStickRand();
        int morphIndex = baseMStick.chooseRandLeaf();
        int noiseIndex = morphIndex;

        //use that trial's base matchstick to generate the rest of the trials
        for (int i = 0; i < parameters.getNumTrials(); i++) {
            ProceduralStim stim = new ProceduralStim(generator, parameters.getProceduralStimParameters(), baseMStick, morphIndex);
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

    public void addFieldsToPanel(JPanel panel){
        this.initFields();
        super.addFieldsToPanel(panel);
        panel.add(new JLabel("numDeltaTrialSets:"));
        panel.add(numDeltaTrialSetsField);
    }

    public void initFields() {
        super.initFields();
        numDeltaTrialSetsField = new JTextField("3", 10);
    }


    public void loadParametersIntoFields(MockExperimentGenParameters blockParams) {
        super.loadParametersIntoFields(blockParams);
        numDeltaTrialSetsField.setText(String.valueOf(((MockExperimentGenParameters) blockParams).numDeltaTrialSets));
    }

    public static class MockExperimentGenParameters extends GenParameters {

        public int numDeltaTrialSets;

        public MockExperimentGenParameters() {
        }

        public MockExperimentGenParameters(NAFCTrialParameters proceduralStimParameters, int numTrials, int numDeltaTrialSets) {
            super(proceduralStimParameters, numTrials);
            this.numDeltaTrialSets = numDeltaTrialSets;
        }

        public MockExperimentGenParameters(GenParameters parameters, int numDeltaTrialSets) {
            super(parameters.getProceduralStimParameters(), parameters.getNumTrials());
            this.numDeltaTrialSets = numDeltaTrialSets;
        }
    }
}