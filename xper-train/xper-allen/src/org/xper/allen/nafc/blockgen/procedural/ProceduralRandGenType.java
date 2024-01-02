package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

import javax.swing.*;
import java.awt.*;
import java.util.*;
import java.util.List;

public class ProceduralRandGenType {
    public static final String label = "RandProcedural";

    protected NAFCBlockGen generator;


    protected JTextField sampleDistMinField, sampleDistMaxField, choiceDistMinField, choiceDistMaxField;
    protected JTextField sizeField, eyeWinSizeField, noiseChanceField, numChoicesField, numRandDistractorsField;
    protected JTextField morphMagnitudeField, morphDiscretenessField, colorRedField, colorGreenField, colorBlueField, numTrialsField;

    public ProceduralRandGenType(NAFCBlockGen generator) {
        this.generator = generator;
    }

    public static ProceduralRandGenType getGenType(String s, NAFCBlockGen proceduralExperimentBlockGen) {
        if (s.equals(MockExperimentGenType.label)) {
            return new MockExperimentGenType(proceduralExperimentBlockGen);
        } else if (s.equals(ProceduralRandGenType.label)) {
            return new ProceduralRandGenType(proceduralExperimentBlockGen);
        } else {
            throw new IllegalArgumentException("Invalid label: " + s);
        }
    }

    public Map.Entry<List<NAFCStim>, ProceduralRandGenParameters> genBlock(){
        ProceduralRandGenParameters params = new ProceduralRandGenParameters(getTrialParameters(), getNumTrials());
        List<NAFCStim> block = genTrials(params);
        return new LinkedHashMap.SimpleEntry<>(block, params);
    }

    private List<NAFCStim> genTrials(ProceduralRandGenParameters proceduralRandGenParameters) {
        List<NAFCStim> newBlock = new LinkedList<>();
        for (int i = 0; i < proceduralRandGenParameters.getNumTrials(); i++) {
            ProceduralStim stim = new ProceduralRandStim(generator, (ProceduralStim.ProceduralStimParameters) proceduralRandGenParameters.getProceduralStimParameters());
            newBlock.add(stim);
        }
        return newBlock;
    }

    public int getNumTrials(){
        return Integer.parseInt(numTrialsField.getText());
    }

    public ProceduralRandGenParameters getParameters(){
        return new ProceduralRandGenParameters(getTrialParameters(), getNumTrials());
    }

    public NAFCTrialParameters getTrialParameters() {
        double sampleDistMin = Double.parseDouble(sampleDistMinField.getText());
        double sampleDistMax = Double.parseDouble(sampleDistMaxField.getText());
        double choiceDistMin = Double.parseDouble(choiceDistMinField.getText());
        double choiceDistMax = Double.parseDouble(choiceDistMaxField.getText());
        double size = Double.parseDouble(sizeField.getText());
        double eyeWinSize = Double.parseDouble(eyeWinSizeField.getText());
        double noiseChance = Double.parseDouble(noiseChanceField.getText());
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
                numChoices,
                numRandDistractors,
                morphMagnitude,
                morphDiscreteness,
                new Color(red, green, blue));
        return proceduralStimParameters;
    }

    public void addParameterFieldsToPanel(JPanel panel) {
        initializeParameterFields();
        panel.add(new JLabel("Sample Distance Lims (Min):"));
        panel.add(sampleDistMinField);
        panel.add(new JLabel("Sample Distance Lims (Max):"));
        panel.add(sampleDistMaxField);
        panel.add(new JLabel("Choice Distance Lims (Min):"));
        panel.add(choiceDistMinField);
        panel.add(new JLabel("Choice Distance Lims (Max):"));
        panel.add(choiceDistMaxField);
        panel.add(new JLabel("Size:"));
        panel.add(sizeField);
        panel.add(new JLabel("Eye Win Size:"));
        panel.add(eyeWinSizeField);
        panel.add(new JLabel("Noise Chance:"));
        panel.add(noiseChanceField);
        panel.add(new JLabel("Number of Choices:"));
        panel.add(numChoicesField);
        panel.add(new JLabel("Number of Random Distractors:"));
        panel.add(numRandDistractorsField);
        panel.add(new JLabel("Morph Magnitude:"));
        panel.add(morphMagnitudeField);
        panel.add(new JLabel("Morph Discreteness:"));
        panel.add(morphDiscretenessField);
        panel.add(new JLabel("Color - Red (0-255):"));
        panel.add(colorRedField);
        panel.add(new JLabel("Color - Green (0-255):"));
        panel.add(colorGreenField);
        panel.add(new JLabel("Color - Blue (0-255):"));
        panel.add(colorBlueField);
        panel.add(new JLabel("Number of Trials:"));
        panel.add(numTrialsField);
    }

    protected void initializeParameterFields() {
        sampleDistMinField = new JTextField("0.0", 10);
        sampleDistMaxField = new JTextField("2.0", 10);
        choiceDistMinField = new JTextField("15.0", 10);
        choiceDistMaxField = new JTextField("15.0", 10);
        sizeField = new JTextField("8.0", 10);
        eyeWinSizeField = new JTextField("10.0", 10);
        noiseChanceField = new JTextField("0.3", 10);
        numChoicesField = new JTextField("4", 10);
        numRandDistractorsField = new JTextField("2", 10);
        morphMagnitudeField = new JTextField("0.5", 10);
        morphDiscretenessField = new JTextField("0.5", 10);
        colorRedField = new JTextField("255", 10);
        colorGreenField = new JTextField("255", 10);
        colorBlueField = new JTextField("255", 10);
        numTrialsField = new JTextField("10", 10);
    }

    public void loadParametersIntoFields(ProceduralRandGenParameters blockParams) {
        ProceduralStim.ProceduralStimParameters stimParameters = (ProceduralStim.ProceduralStimParameters) blockParams.getProceduralStimParameters();
        if (stimParameters != null) {
            sampleDistMinField.setText(String.valueOf(stimParameters.getSampleDistanceLims().getLowerLim()));
            sampleDistMaxField.setText(String.valueOf(stimParameters.getSampleDistanceLims().getUpperLim()));
            choiceDistMinField.setText(String.valueOf(stimParameters.getChoiceDistanceLims().getLowerLim()));
            choiceDistMaxField.setText(String.valueOf(stimParameters.getChoiceDistanceLims().getUpperLim()));
            sizeField.setText(String.valueOf(stimParameters.getSize()));
            eyeWinSizeField.setText(String.valueOf(stimParameters.getEyeWinSize()));
            noiseChanceField.setText(String.valueOf(stimParameters.noiseChance));
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


    public String getInfo(){
        return "Type: " + getLabel() +
                ", Trials: " + getNumTrials() +
                ", NoiseChance: " + noiseChanceField.getText() +
                ", NumChoices: " + numChoicesField.getText() +
                ", NumRandDistractors: " + numRandDistractorsField.getText();
    }

    public String getLabel(){
        return label;
    }
}