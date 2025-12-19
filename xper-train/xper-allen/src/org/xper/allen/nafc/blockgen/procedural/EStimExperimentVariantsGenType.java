package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.pga.EStimShapeVariantsStim;

import javax.swing.*;
import java.util.LinkedList;
import java.util.List;

public class EStimExperimentVariantsGenType extends ProceduralRandGenType<EStimExperimentGenType.EStimExperimentGenParameters>{
    protected JTextField stimIdField;
    protected JTextField isEStimEnabledField;

    public EStimExperimentVariantsGenType() {
        super();
    }

    public String getLabel() {
        return "EStimExperimentVariants";
    }

    public EStimExperimentGenType.EStimExperimentGenParameters readFromFields() {
        long stimId = Long.parseLong(stimIdField.getText());
        boolean isEStimEnabled = Boolean.parseBoolean(isEStimEnabledField.getText());
        EStimExperimentGenType.EStimExperimentGenParameters params = new EStimExperimentGenType.EStimExperimentGenParameters(super.readFromFields(), 0, stimId, -1, isEStimEnabled);
        return params;
    }

    @Override
    protected List<NAFCStim> genTrials(EStimExperimentGenType.EStimExperimentGenParameters parameters) {
        List<NAFCStim> newBlock = new LinkedList<>();

        int morphIndex = parameters.compId;
        int noiseIndex = morphIndex;

        //use that trial's base matchstick to generate the rest of the trials
        for (int i = 0; i < parameters.getNumTrials(); i++) {
            if (parameters.stimId == 0){
                newBlock.add(EStimShapeVariantsNAFCStim.createSampledIdEStimShapeVariantsNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        parameters.isEStimEnabled));
            } else {
                //using estim value from the GUI field
                EStimShapeVariantsNAFCStim stim = new EStimShapeVariantsNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        parameters.stimId,
                        parameters.isEStimEnabled);
                newBlock.add(stim);
            }
        }
        return newBlock;
    }

    public void initFields(){
        super.initFields();
        stimIdField = new JTextField("0", 10);
        isEStimEnabledField = new JTextField("true", 10);

        labelsForFields.put(stimIdField, "stimId:");
        defaultsForFields.put(stimIdField, "0");

        labelsForFields.put(isEStimEnabledField, "isEStimEnabled (true/false):");
        defaultsForFields.put(isEStimEnabledField, "false");
    }

    @Override
    public void loadParametersIntoFields(GenParameters blockParams) {
        super.loadParametersIntoFields(blockParams);
        stimIdField.setText(String.valueOf(((EStimExperimentGenType.EStimExperimentGenParameters) blockParams).stimId));
        isEStimEnabledField.setText(String.valueOf(((EStimExperimentGenType.EStimExperimentGenParameters) blockParams).isEStimEnabled));
    }

}
