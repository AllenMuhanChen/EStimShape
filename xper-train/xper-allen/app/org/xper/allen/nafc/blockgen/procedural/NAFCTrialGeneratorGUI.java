package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;
import java.awt.*;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;

public class NAFCTrialGeneratorGUI {
    private static JPanel centerPanel;
    private static final DefaultListModel<String> listModel = new DefaultListModel<>();
    private static ProceduralRandGenType selectedType;

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

        List<? extends ProceduralRandGenType> stimTypes = Arrays.asList(new ProceduralRandGenType(blockgen), new MockExperimentGenType(blockgen));
        HashMap<String, ProceduralRandGenType> labelsForStimTypes = new HashMap<>();
        for (ProceduralRandGenType stimType : stimTypes) {
            labelsForStimTypes.put(stimType.getLabel(), stimType);
        }
        ProceduralRandGenType defaultStimType = labelsForStimTypes.get("RandProcedural");
        selectedType = defaultStimType;

        JFrame frame = new JFrame("Trial Generator");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setSize(1000, 600);

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

        trialList.addListSelectionListener(e -> {
            if (!e.getValueIsAdjusting()) {
                int selectedIndex = trialList.getSelectedIndex();
                if (selectedIndex != -1) {
                    selectedType.loadParametersIntoFields(blockgen.getParamsForBlock(selectedIndex));
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
            blockgen.addBlock(selectedType.genBlock());
            listModel.addElement(selectedType.getInfo());
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
                blockgen.editBlock(selectedIndex, selectedType.genBlock());
                listModel.set(selectedIndex, selectedType.getInfo());
            }
        });

        frame.getContentPane().add(BorderLayout.NORTH, topPanel);
        frame.getContentPane().add(BorderLayout.WEST, centerPanel);
        frame.getContentPane().add(BorderLayout.CENTER, listScrollPane);
        frame.getContentPane().add(BorderLayout.SOUTH, bottomPanel);
        frame.setVisible(true);
    }


    private static void updateParametersUI(ProceduralRandGenType selectedType) {
        centerPanel.removeAll();
        selectedType.addParameterFieldsToPanel(centerPanel);
        centerPanel.revalidate();
        centerPanel.repaint();
    }
}