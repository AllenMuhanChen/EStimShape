package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;
import java.awt.*;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;

public class TrialGeneratorGUI {
    private static JPanel centerPanel;
    private static DefaultListModel<String> listModel = new DefaultListModel<>();
    private static RandStimType selectedType;
    private static List<? extends RandStimType> stimTypes;

    public static <Map> void main(String[] args) {
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception e) {
            throw new XGLException(e);
        }
        FileUtil.loadTestSystemProperties("/xper.properties.procedural");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));
        ProceduralExperimentBlockGen blockgen = context.getBean(ProceduralExperimentBlockGen.class);

        stimTypes = Arrays.asList(new RandStimType(blockgen));
        HashMap<String, RandStimType> labelsForStimTypes = new HashMap<>();
        for (RandStimType stimType : stimTypes) {
            labelsForStimTypes.put(stimType.label, stimType);
        }
        RandStimType defaultStimType = labelsForStimTypes.get("Rand");
        selectedType = defaultStimType;

        JFrame frame = new JFrame("Trial Generator");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setSize(500, 600);

        JPanel topPanel = new JPanel();
        JLabel stimTypeLabel = new JLabel("Select Stimulus Type:");


        JComboBox<String> stimTypeDropdown = new JComboBox<>(labelsForStimTypes.keySet().toArray(new String[0]));
        topPanel.add(stimTypeLabel);
        topPanel.add(stimTypeDropdown);

        centerPanel = new JPanel(new GridLayout(0, 2));
        updateParametersUI(defaultStimType);

        stimTypeDropdown.addActionListener(e -> {
            String selectedLabel = (String) stimTypeDropdown.getSelectedItem();
            selectedType = labelsForStimTypes.get(selectedLabel);
            updateParametersUI(selectedType);
        });

        JList<String> trialList = new JList<>(listModel);
        JScrollPane listScrollPane = new JScrollPane(trialList);
        listScrollPane.setPreferredSize(new Dimension(400, 100));

        trialList.addListSelectionListener(e -> {
            if (!e.getValueIsAdjusting()) {
                int selectedIndex = trialList.getSelectedIndex();
                if (selectedIndex != -1) {
                    ProceduralStim.ProceduralStimParameters parameters = blockgen.getBlockParameters(selectedIndex);
                    int numTrials = blockgen.getNumTrials(selectedIndex);
                    selectedType.loadParametersIntoFields(parameters, numTrials);

                }
            }
        });

        JPanel bottomPanel = new JPanel();
        JButton addTrialsButton = new JButton("Add Trials");
        JButton generateButton = new JButton("Generate Trials");
        JButton removeButton = new JButton("Remove Selected Trial");
        JButton editButton = new JButton("Edit Selected Trial");

        bottomPanel.add(addTrialsButton);
        bottomPanel.add(generateButton);
        bottomPanel.add(removeButton);
        bottomPanel.add(editButton);

        addTrialsButton.addActionListener(e -> {
            ProceduralStim.ProceduralStimParameters proceduralStimParameters =
                    selectedType.getProceduralStimParameters();
            int numTrials = selectedType.getNumTrials();

            blockgen.addBlock(selectedType.genTrials(proceduralStimParameters, numTrials));
            listModel.addElement("Type: " + selectedType.label + ", Trials: " + numTrials);

        });

        generateButton.addActionListener(e -> blockgen.generate());

        removeButton.addActionListener(e -> {
            int selectedIndex = trialList.getSelectedIndex();
            if (selectedIndex != -1) {
                listModel.remove(selectedIndex);
                blockgen.removeBlock(selectedIndex);
            }
        });

        editButton.addActionListener(e -> {
            int selectedIndex = trialList.getSelectedIndex();
            if (selectedIndex != -1) {
                ProceduralStim.ProceduralStimParameters parameters = selectedType.getProceduralStimParameters();
                int numTrials = selectedType.getNumTrials();
                blockgen.editBlock(selectedIndex, selectedType.genTrials(parameters, numTrials));
                listModel.set(selectedIndex, "Type: " + selectedType.label + ", Trials: " + numTrials);
            }
        });

        frame.getContentPane().add(BorderLayout.NORTH, topPanel);
        frame.getContentPane().add(BorderLayout.CENTER, centerPanel);
        frame.getContentPane().add(BorderLayout.EAST, listScrollPane);
        frame.getContentPane().add(BorderLayout.SOUTH, bottomPanel);
        frame.setVisible(true);
    }


    private static void updateParametersUI(RandStimType selectedType) {
        centerPanel.removeAll();
        selectedType.addParameterFieldsToPanel(centerPanel);
        centerPanel.revalidate();
        centerPanel.repaint();
    }
}