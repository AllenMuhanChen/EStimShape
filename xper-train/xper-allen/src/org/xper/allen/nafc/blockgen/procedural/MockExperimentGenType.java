package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.drawing.composition.experiment.ExperimentMatchStick;
import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

import javax.swing.*;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class MockExperimentGenType extends ProceduralRandGenType{
    public static final String label = "MockProcedural";

    protected JTextField numDeltaTrialSetsField;

    public MockExperimentGenType(ProceduralExperimentBlockGen generator) {
        super(generator);
    }

//    public Map.Entry<List<NAFCStim>, ProceduralRandGenParameters> genBlock(){
//        int numDeltaTrialSets = Integer.parseInt(numDeltaTrialSetsField.getText());
//        return genTrials(getParameters(), getNumTrials(), numDeltaTrialSets);
//    }

    private List<NAFCStim> genTrials(NAFCTrialParameters parameters, int numTrials, int numDeltaTrialSets) {
        List<NAFCStim> newBlock = new LinkedList<>();

        //ADD PROCEDURAL TRIALS
        ExperimentMatchStick baseMStick;
        int morphIndex;
        int noiseIndex;

        //generate first trial (to have a base matchstick that completed generation fine)
        ProceduralStim firstStim = new ProceduralRandStim(generator, (ProceduralStim.ProceduralStimParameters) parameters);
        baseMStick = firstStim.baseMatchStick;
        morphIndex = firstStim.morphComponentIndex;
        noiseIndex = firstStim.noiseComponentIndex;

        //use that trial's base matchstick to generate the rest of the trials
        for (int i = 1; i < numTrials; i++) {
            ProceduralStim stim = new ProceduralStim(generator, (ProceduralStim.ProceduralStimParameters) parameters, baseMStick, morphIndex, noiseIndex);
            newBlock.add(stim);
        }

        //ADD DELTA TRIALS
        //choose random trials to make delta trials from
        for (int i=0; i<numDeltaTrialSets; i++){
            int randIndex = (int) (Math.random() * numTrials);
            ProceduralStim baseStim = (ProceduralStim) newBlock.get(randIndex);
            newBlock.add(DeltaStim.createDeltaNoise(baseStim));
            newBlock.add(DeltaStim.createDeltaMorph(baseStim));
            newBlock.add(DeltaStim.createDeltaNoiseDeltaMorph(baseStim));
        }
        return newBlock;
    }

    public void addParameterFieldsToPanel(JPanel panel){
        initializeParameterFields();
        panel.add(new JLabel("numDeltaTrialSets:"));
        panel.add(numDeltaTrialSetsField);
    }

    protected void initializeParameterFields() {
        super.initializeParameterFields();
        numDeltaTrialSetsField = new JTextField("3", 10);
    }

    public void loadParametersIntoFields(List<NAFCStim> block) {
        if (block != null) {
            ProceduralStim.ProceduralStimParameters parameters = (ProceduralStim.ProceduralStimParameters) block.get(0).getParameters();
            loadParametersIntoFields(parameters, block.size());
        }
    }
}