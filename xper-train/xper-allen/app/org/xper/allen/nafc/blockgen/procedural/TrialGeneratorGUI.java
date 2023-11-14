package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;
import org.xper.allen.nafc.blockgen.procedural.ProceduralExperimentBlockGen;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

public class TrialGeneratorGUI {

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

        // Creating the frame
        JFrame frame = new JFrame("Trial Generator");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setSize(500, 500);

        // Creating the panel at bottom and adding components
        JPanel panel = new JPanel();
        JLabel label = new JLabel("Enter Parameters");
        JButton addRandTrainTrialsButton = new JButton("Add Rand Train Trials");
        JButton generateButton = new JButton("Generate Trials");
        panel.add(label);
        panel.add(addRandTrainTrialsButton);
        panel.add(generateButton);

        // Creating the panel at center and adding components
        JPanel centerPanel = new JPanel(new GridLayout(11, 2));
        centerPanel.add(new JLabel("Sample Distance Lims (Min):"));
        JTextField sampleDistMinField = new JTextField("0.0", 10);
        centerPanel.add(sampleDistMinField);

        centerPanel.add(new JLabel("Sample Distance Lims (Max):"));
        JTextField sampleDistMaxField = new JTextField("2.0", 10);
        centerPanel.add(sampleDistMaxField);

        centerPanel.add(new JLabel("Choice Distance Lims (Min):"));
        JTextField choiceDistMinField = new JTextField("8.0", 10);
        centerPanel.add(choiceDistMinField);

        centerPanel.add(new JLabel("Choice Distance Lims (Max):"));
        JTextField choiceDistMaxField = new JTextField("10.0", 10);
        centerPanel.add(choiceDistMaxField);

        centerPanel.add(new JLabel("Size:"));
        JTextField sizeField = new JTextField("8.0", 10);
        centerPanel.add(sizeField);

        centerPanel.add(new JLabel("Eye Win Size:"));
        JTextField eyeWinSizeField = new JTextField("10.0", 10);
        centerPanel.add(eyeWinSizeField);

        centerPanel.add(new JLabel("Noise Chance:"));
        JTextField noiseChanceField = new JTextField("0.5", 10);
        centerPanel.add(noiseChanceField);

        centerPanel.add(new JLabel("Number of Choices:"));
        JTextField numChoicesField = new JTextField("4", 10);
        centerPanel.add(numChoicesField);

        centerPanel.add(new JLabel("Number of Random Distractors:"));
        JTextField numRandDistractorsField = new JTextField("1", 10);
        centerPanel.add(numRandDistractorsField);

        centerPanel.add(new JLabel("Morph Magnitude:"));
        JTextField morphMagnitudeField = new JTextField("0.5", 10);
        centerPanel.add(morphMagnitudeField);

        centerPanel.add(new JLabel("Color (RGB):"));
        JTextField colorField = new JTextField("#FF0000", 10); // Default for red color
        centerPanel.add(colorField);

        centerPanel.add(new JLabel("Number of Trials:"));
        JTextField numTrialsField = new JTextField("10", 10);
        centerPanel.add(numTrialsField);

        // Adding action listener for the 'Add Rand Train Trials' button
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
                Color color = Color.decode(colorField.getText());
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
                        color);

                blockgen.addRandTrainTrials(proceduralStimParameters, numTrials);
            }
        });

        // Modifying the action listener for the 'Generate Trials' button
        generateButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                blockgen.generate();
            }
        });

        // Adding Panels to Frame
        frame.getContentPane().add(BorderLayout.SOUTH, panel);
        frame.getContentPane().add(BorderLayout.CENTER, centerPanel);
        frame.setVisible(true);
    }
}