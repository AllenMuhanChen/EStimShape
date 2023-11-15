package org.xper.allen.nafc.blockgen.procedural;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

public class TrialGeneratorGUI {

    private static JTextField sampleDistMinField, sampleDistMaxField, choiceDistMinField, choiceDistMaxField;
    private static JTextField sizeField, eyeWinSizeField, noiseChanceField, numChoicesField, numRandDistractorsField;
    private static JTextField morphMagnitudeField, colorRedField, colorGreenField, colorBlueField, numTrialsField;
    private static JPanel centerPanel;

    public static void main(String[] args) {
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception e) {
            throw new XGLException(e);
        }
        FileUtil.loadTestSystemProperties("/xper.properties.procedural");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));
        ProceduralExperimentBlockGen blockgen = context.getBean(ProceduralExperimentBlockGen.class);

        JFrame frame = new JFrame("Trial Generator");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setSize(500, 600);

        JPanel topPanel = new JPanel();
        JLabel stimTypeLabel = new JLabel("Select Stimulus Type:");
        String[] stimTypes = {"RandStim", "MockStim", "OtherStimType2"};
        JComboBox<String> stimTypeDropdown = new JComboBox<>(stimTypes);
        topPanel.add(stimTypeLabel);
        topPanel.add(stimTypeDropdown);

        centerPanel = new JPanel(new GridLayout(0, 2));
        initializeParameterFields();
        updateParametersUI("RandStim");

        stimTypeDropdown.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                String selectedType = (String) stimTypeDropdown.getSelectedItem();
                updateParametersUI(selectedType);
            }
        });

        JPanel bottomPanel = new JPanel();
        JButton addRandTrainTrialsButton = new JButton("Add Trials");
        JButton generateButton = new JButton("Generate Trials");
        bottomPanel.add(addRandTrainTrialsButton);
        bottomPanel.add(generateButton);

        addRandTrainTrialsButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
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
                int red = Integer.parseInt(colorRedField.getText());
                int green = Integer.parseInt(colorGreenField.getText());
                int blue = Integer.parseInt(colorBlueField.getText());
                int numTrials = Integer.parseInt(numTrialsField.getText());

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
                        new Color(red, green, blue));

                if ("RandStim".equals(stimTypeDropdown.getSelectedItem())) {
                    blockgen.addRandTrainTrials(proceduralStimParameters, numTrials);
                } else if ("MockStim".equals(stimTypeDropdown.getSelectedItem())) {
                    blockgen.addMockTrainTrials(proceduralStimParameters, numTrials);
                }

            }
        });

        generateButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                blockgen.generate();
            }
        });

        frame.getContentPane().add(BorderLayout.NORTH, topPanel);
        frame.getContentPane().add(BorderLayout.CENTER, centerPanel);
        frame.getContentPane().add(BorderLayout.SOUTH, bottomPanel);
        frame.setVisible(true);
    }

    private static void initializeParameterFields() {
        sampleDistMinField = new JTextField("0.0", 10);
        sampleDistMaxField = new JTextField("10.0", 10);
        choiceDistMinField = new JTextField("0.0", 10);
        choiceDistMaxField = new JTextField("10.0", 10);
        sizeField = new JTextField("5.0", 10);
        eyeWinSizeField = new JTextField("2.0", 10);
        noiseChanceField = new JTextField("0.1", 10);
        numChoicesField = new JTextField("3", 10);
        numRandDistractorsField = new JTextField("1", 10);
        morphMagnitudeField = new JTextField("0.5", 10);
        colorRedField = new JTextField("255", 10);
        colorGreenField = new JTextField("0", 10);
        colorBlueField = new JTextField("0", 10);
        numTrialsField = new JTextField("10", 10);
    }

    private static void updateParametersUI(String stimType) {
        centerPanel.removeAll();
        centerPanel.add(new JLabel("Sample Distance Lims (Min):"));
        centerPanel.add(sampleDistMinField);
        centerPanel.add(new JLabel("Sample Distance Lims (Max):"));
        centerPanel.add(sampleDistMaxField);
        centerPanel.add(new JLabel("Choice Distance Lims (Min):"));
        centerPanel.add(choiceDistMinField);
        centerPanel.add(new JLabel("Choice Distance Lims (Max):"));
        centerPanel.add(choiceDistMaxField);
        centerPanel.add(new JLabel("Size:"));
        centerPanel.add(sizeField);
        centerPanel.add(new JLabel("Eye Win Size:"));
        centerPanel.add(eyeWinSizeField);
        centerPanel.add(new JLabel("Noise Chance:"));
        centerPanel.add(noiseChanceField);
        centerPanel.add(new JLabel("Number of Choices:"));
        centerPanel.add(numChoicesField);
        centerPanel.add(new JLabel("Number of Random Distractors:"));
        centerPanel.add(numRandDistractorsField);
        centerPanel.add(new JLabel("Morph Magnitude:"));
        centerPanel.add(morphMagnitudeField);
        centerPanel.add(new JLabel("Color - Red (0-255):"));
        centerPanel.add(colorRedField);
        centerPanel.add(new JLabel("Color - Green (0-255):"));
        centerPanel.add(colorGreenField);
        centerPanel.add(new JLabel("Color - Blue (0-255):"));
        centerPanel.add(colorBlueField);
        centerPanel.add(new JLabel("Number of Trials:"));
        centerPanel.add(numTrialsField);

        if ("MockStim".equals(stimType)) {
            centerPanel.add(new JLabel("OtherStimType1 Field 1:"));
            centerPanel.add(new JTextField("OtherStimType1 Field 1", 10));
        } else if ("OtherStimType2".equals(stimType)) {
            // Add specific fields for OtherStimType2
        }

        centerPanel.revalidate();
        centerPanel.repaint();
    }
}