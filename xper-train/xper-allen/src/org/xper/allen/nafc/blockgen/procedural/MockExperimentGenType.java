package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

import javax.swing.*;
import java.util.*;
import java.util.List;

public class MockExperimentGenType extends ProceduralRandGenType{
    public static final String label = "MockProcedural";

    protected JTextField numDeltaTrialSetsField;

    public MockExperimentGenType(ProceduralExperimentBlockGen generator) {
        super(generator);
    }

    public Map.Entry<List<NAFCStim>, ProceduralRandGenParameters> genBlock(){
        int numDeltaTrialSets = Integer.parseInt(numDeltaTrialSetsField.getText());
        MockExperimentGenParameters params = new MockExperimentGenParameters(getParameters(), getNumTrials(), numDeltaTrialSets);
        List<NAFCStim> newBlock = genTrials(params, getNumTrials(), numDeltaTrialSets);

        return new AbstractMap.SimpleEntry<>(newBlock, params);
    }

    private List<NAFCStim> genTrials(ProceduralRandGenParameters genParameters, int numTrials, int numDeltaTrialSets) {
        List<NAFCStim> newBlock = new LinkedList<>();


        //Generate the base matchstick
        ProceduralMatchStick baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(generator.getMaxImageDimensionDegrees());
        baseMStick.setStimColor(genParameters.getProceduralStimParameters().color);
        baseMStick.genMatchStickRand();
        int morphIndex = baseMStick.chooseRandLeaf();
        int noiseIndex = morphIndex;

        //use that trial's base matchstick to generate the rest of the trials
        for (int i = 0; i < numTrials; i++) {
            ProceduralStim stim = new ProceduralStim(generator, genParameters.getProceduralStimParameters(), baseMStick, morphIndex, noiseIndex);
            newBlock.add(stim);
        }

        //ADD DELTA TRIALS
        //choose random trials to make delta trials from
        for (int i=0; i<numDeltaTrialSets; i++){
            int randIndex = (int) (Math.random() * numTrials);
            ProceduralStim baseStim = (ProceduralStim) newBlock.get(randIndex);
            ProceduralStim deltaMorph = new DeltaStim(baseStim, true, false);
            ProceduralStim deltaNoise = new DeltaStim(baseStim, false, true);
            ProceduralStim deltaBoth = new DeltaStim(baseStim, true, true);
            newBlock.add(deltaMorph);
            newBlock.add(deltaNoise);
            newBlock.add(deltaBoth);
        }
        return newBlock;
    }

    public void addParameterFieldsToPanel(JPanel panel){
        initializeParameterFields();
        super.addParameterFieldsToPanel(panel);
        panel.add(new JLabel("numDeltaTrialSets:"));
        panel.add(numDeltaTrialSetsField);
    }

    protected void initializeParameterFields() {
        super.initializeParameterFields();
        numDeltaTrialSetsField = new JTextField("3", 10);
    }


    public void loadParametersIntoFields(MockExperimentGenParameters blockParams) {
        super.loadParametersIntoFields(blockParams);
        numDeltaTrialSetsField.setText(String.valueOf(((MockExperimentGenParameters) blockParams).numDeltaTrialSets));
    }

    @Override
    public String getLabel(){
        return label;
    }



    public static class MockExperimentGenParameters extends ProceduralRandGenParameters{

        private final int numDeltaTrialSets;

        public MockExperimentGenParameters(NAFCTrialParameters proceduralStimParameters, int numTrials, int numDeltaTrialSets) {
            super(proceduralStimParameters, numTrials);
            this.numDeltaTrialSets = numDeltaTrialSets;
        }
    }
}