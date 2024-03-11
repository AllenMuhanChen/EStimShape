package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

import javax.swing.*;
import java.awt.*;
import java.util.*;
import java.util.List;

public class ProceduralRandGenType<T extends GenParameters> extends GenType<T>{

    protected NAFCBlockGen generator;

    protected JTextField sampleDistMinField, sampleDistMaxField, choiceDistMinField, choiceDistMaxField;
    protected JTextField sizeField, eyeWinSizeField, noiseChanceField, numChoicesField, numRandDistractorsField;
    protected JTextField morphMagnitudeField, morphDiscretenessField, colorRedField, colorGreenField, colorBlueField, numTrialsField;
    protected JTextField noiseRateField;

    public ProceduralRandGenType(NAFCBlockGen generator) {
        this.generator = generator;
    }

    public ProceduralRandGenType() {
    }

    @Override
    public String getLabel() {
        return "RandProcedural";
    }

    /**
     * Populate the labelsForFields and defaultsForFields maps
     */
    public void initFields(){
        sampleDistMinField = new JTextField(10);
        sampleDistMaxField = new JTextField(10);
        choiceDistMinField = new JTextField(10);
        choiceDistMaxField = new JTextField(10);
        sizeField = new JTextField(10);
        eyeWinSizeField = new JTextField(10);
        noiseChanceField = new JTextField(10);
        noiseRateField = new JTextField(10);
        numChoicesField = new JTextField(10);
        numRandDistractorsField = new JTextField(10);
        morphMagnitudeField = new JTextField(10);
        morphDiscretenessField = new JTextField(10);
        colorRedField = new JTextField(10);
        colorGreenField = new JTextField(10);
        colorBlueField = new JTextField(10);
        numTrialsField = new JTextField(10);

        labelsForFields = new LinkedHashMap<>();
        defaultsForFields = new LinkedHashMap<>();

        labelsForFields.put(sampleDistMinField, "Sample Distance Lims (Min):"); defaultsForFields.put(sampleDistMinField, "0.0");
        labelsForFields.put(sampleDistMaxField, "Sample Distance Lims (Max):"); defaultsForFields.put(sampleDistMaxField, "0.0");
        labelsForFields.put(choiceDistMinField, "Choice Distance Lims (Min):"); defaultsForFields.put(choiceDistMinField, "15.0");
        labelsForFields.put(choiceDistMaxField, "Choice Distance Lims (Max):"); defaultsForFields.put(choiceDistMaxField, "15.0");
        labelsForFields.put(sizeField, "Size:"); defaultsForFields.put(sizeField, "5.0");
        labelsForFields.put(eyeWinSizeField, "Eye Win Size:"); defaultsForFields.put(eyeWinSizeField, "9.0");
        labelsForFields.put(noiseChanceField, "Noise Chance:"); defaultsForFields.put(noiseChanceField, "0.2");
        labelsForFields.put(noiseRateField, "Noise Rate:"); defaultsForFields.put(noiseRateField, "1");
        labelsForFields.put(numChoicesField, "Number of Choices:"); defaultsForFields.put(numChoicesField, "4");
        labelsForFields.put(numRandDistractorsField, "Number of Random Distractors:"); defaultsForFields.put(numRandDistractorsField, "2");
        labelsForFields.put(morphMagnitudeField, "Morph Magnitude:"); defaultsForFields.put(morphMagnitudeField, "0.6");
        labelsForFields.put(morphDiscretenessField, "Morph Discreteness:"); defaultsForFields.put(morphDiscretenessField, "0.5");
        labelsForFields.put(colorRedField, "Color - Red (0-255):"); defaultsForFields.put(colorRedField, "255");
        labelsForFields.put(colorGreenField, "Color - Green (0-255):"); defaultsForFields.put(colorGreenField, "255");
        labelsForFields.put(colorBlueField, "Color - Blue (0-255):"); defaultsForFields.put(colorBlueField, "255");
        labelsForFields.put(numTrialsField, "Number of Trials:"); defaultsForFields.put(numTrialsField, "10");
    }

    public void loadParametersIntoFields(GenParameters blockParams) {
        ProceduralStim.ProceduralStimParameters stimParameters = (ProceduralStim.ProceduralStimParameters) blockParams.getProceduralStimParameters();
        if (stimParameters != null) {
            sampleDistMinField.setText(String.valueOf(stimParameters.getSampleDistanceLims().getLowerLim()));
            sampleDistMaxField.setText(String.valueOf(stimParameters.getSampleDistanceLims().getUpperLim()));
            choiceDistMinField.setText(String.valueOf(stimParameters.getChoiceDistanceLims().getLowerLim()));
            choiceDistMaxField.setText(String.valueOf(stimParameters.getChoiceDistanceLims().getUpperLim()));
            sizeField.setText(String.valueOf(stimParameters.getSize()));
            eyeWinSizeField.setText(String.valueOf(stimParameters.getEyeWinSize()));
            noiseChanceField.setText(String.valueOf(stimParameters.noiseChance));
            noiseRateField.setText(String.valueOf(stimParameters.noiseRate));
            numChoicesField.setText(String.valueOf(stimParameters.numChoices));
            numRandDistractorsField.setText(String.valueOf(stimParameters.numRandDistractors));
            morphMagnitudeField.setText(String.valueOf(stimParameters.morphMagnitude));
            morphDiscretenessField.setText(String.valueOf(stimParameters.morphDiscreteness));

            Color color = stimParameters.color;
            colorRedField.setText(String.valueOf(color.getRed()));
            colorGreenField.setText(String.valueOf(color.getGreen()));
            colorBlueField.setText(String.valueOf(color.getBlue()));

            // Assuming there is a way to get the number of trials from the parameters
            // If not, you might need to pass this as a separate parameter
            numTrialsField.setText(String.valueOf(blockParams.getNumTrials()));
        }
    }
    protected List<NAFCStim> genTrials(T genParameters) {
        List<NAFCStim> newBlock = new LinkedList<>();
        for (int i = 0; i < genParameters.getNumTrials(); i++) {
            ProceduralStim stim = new ProceduralRandStim(generator, (ProceduralStim.ProceduralStimParameters) genParameters.getProceduralStimParameters());
            newBlock.add(stim);
        }
        return newBlock;
    }


    public T readFromFields(){
        return (T) new GenParameters(getTrialParameters(), getNumTrials());
    }


    public NAFCTrialParameters getTrialParameters() {
        double sampleDistMin = Double.parseDouble(sampleDistMinField.getText());
        double sampleDistMax = Double.parseDouble(sampleDistMaxField.getText());
        double choiceDistMin = Double.parseDouble(choiceDistMinField.getText());
        double choiceDistMax = Double.parseDouble(choiceDistMaxField.getText());
        double size = Double.parseDouble(sizeField.getText());
        double eyeWinSize = Double.parseDouble(eyeWinSizeField.getText());
        double noiseChance = Double.parseDouble(noiseChanceField.getText());
        double noiseRate = Double.parseDouble(noiseRateField.getText());
        int numChoices = Integer.parseInt(numChoicesField.getText());
        int numRandDistractors = Integer.parseInt(numRandDistractorsField.getText());
        double morphMagnitude = Double.parseDouble(morphMagnitudeField.getText());
        double morphDiscreteness = Double.parseDouble(morphDiscretenessField.getText());
        int red = Integer.parseInt(colorRedField.getText());
        int green = Integer.parseInt(colorGreenField.getText());
        int blue = Integer.parseInt(colorBlueField.getText());

        Lims sampleDistanceLims = new Lims(sampleDistMin, sampleDistMax);
        Lims choiceDistanceLims = new Lims(choiceDistMin, choiceDistMax);

        NAFCTrialParameters nafcTrialParameters = new NAFCTrialParameters(
                sampleDistanceLims,
                choiceDistanceLims,
                size,
                eyeWinSize);
        ProceduralStim.ProceduralStimParameters proceduralStimParameters = new ProceduralStim.ProceduralStimParameters(
                nafcTrialParameters,
                noiseChance,
                noiseRate,
                numChoices,
                numRandDistractors,
                morphMagnitude,
                morphDiscreteness,
                new Color(red, green, blue));
        return proceduralStimParameters;
    }


    public int getNumTrials(){
        return Integer.parseInt(numTrialsField.getText());
    }

    public void setGenerator(NAFCBlockGen generator) {
        this.generator = generator;
    }

    public String getInfo(){
        return "Type: " + getLabel() +
                ", Trials: " + getNumTrials() +
                ", NoiseChance: " + noiseChanceField.getText() +
                ", NumChoices: " + numChoicesField.getText() +
                ", NumRandDistractors: " + numRandDistractorsField.getText();
    }
}