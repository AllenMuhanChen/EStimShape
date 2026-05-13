package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.nafc.NAFCStim;

import javax.swing.*;
import java.util.LinkedList;
import java.util.List;

public class EStimExperimentVariantsGenType extends ProceduralRandGenType<EStimExperimentGenType.EStimExperimentGenParameters>{
    protected JTextField stimIdField;
    protected JTextField isEStimEnabledField;
    protected JTextField eStimSpecIdField;
    protected JTextField includeRemovedChoiceField;

    public EStimExperimentVariantsGenType() {
        super();
    }

    public String getLabel() {
        return "EStimExperimentVariants";
    }

    public EStimExperimentGenType.EStimExperimentGenParameters readFromFields() {
        long stimId = Long.parseLong(stimIdField.getText());
        boolean isEStimEnabled = Boolean.parseBoolean(isEStimEnabledField.getText());
        long eStimSpecId = Long.parseLong(eStimSpecIdField.getText());
        boolean includeRemovedChoice = Boolean.parseBoolean(includeRemovedChoiceField.getText());
        EStimExperimentGenType.EStimExperimentGenParameters params = new EStimExperimentGenType.EStimExperimentGenParameters(
                super.readFromFields(), 0, stimId, -1, isEStimEnabled, eStimSpecId);
        params.includeRemovedChoice = includeRemovedChoice;
        return params;
    }

    @Override
    protected List<NAFCStim> genTrials(EStimExperimentGenType.EStimExperimentGenParameters parameters) {
        List<NAFCStim> newBlock = new LinkedList<>();

        int morphIndex = parameters.compId;
        int noiseIndex = morphIndex;

        //use that trial's base matchstick to generate the rest of the trials
        for (int i = 0; i < parameters.getNumTrials(); i++) {
            EStimShapeVariantsNAFCStim stim;
            if (parameters.stimId == 0){
                stim = EStimShapeVariantsNAFCStim.createSampledIdEStimShapeVariantsNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        parameters.isEStimEnabled, parameters.eStimSpecId);
            } else {
                //using estim value from the GUI field
                stim = new EStimShapeVariantsNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        parameters.stimId,
                        parameters.isEStimEnabled, parameters.eStimSpecId);
            }
            stim.setIncludeRemovedChoice(parameters.includeRemovedChoice);
            newBlock.add(stim);
        }
        return newBlock;
    }

    public void initFields(){
        super.initFields();
        stimIdField = new JTextField("0", 10);
        isEStimEnabledField = new JTextField("true", 10);
        eStimSpecIdField = new JTextField("0", 10);
        includeRemovedChoiceField = new JTextField("false", 10);

        labelsForFields.put(stimIdField, "stimId:");
        defaultsForFields.put(stimIdField, "0");

        labelsForFields.put(isEStimEnabledField, "isEStimEnabled (true/false):");
        defaultsForFields.put(isEStimEnabledField, "false");

        labelsForFields.put(eStimSpecIdField, "eStimSpecId:");
        defaultsForFields.put(eStimSpecIdField, "0");

        labelsForFields.put(includeRemovedChoiceField, "includeRemovedChoice (true/false):");
        defaultsForFields.put(includeRemovedChoiceField, "false");
    }

    @Override
    public void loadParametersIntoFields(GenParameters blockParams) {
        super.loadParametersIntoFields(blockParams);
        stimIdField.setText(String.valueOf(((EStimExperimentGenType.EStimExperimentGenParameters) blockParams).stimId));
        isEStimEnabledField.setText(String.valueOf(((EStimExperimentGenType.EStimExperimentGenParameters) blockParams).isEStimEnabled));
        eStimSpecIdField.setText(String.valueOf(((EStimExperimentGenType.EStimExperimentGenParameters) blockParams).eStimSpecId));
        includeRemovedChoiceField.setText(String.valueOf(((EStimExperimentGenType.EStimExperimentGenParameters) blockParams).includeRemovedChoice));
    }

}
