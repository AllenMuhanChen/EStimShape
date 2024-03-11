package org.xper.allen.app.procedural;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.nafc.blockgen.procedural.*;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.*;
import java.util.List;

public class NAFCTrialGeneratorGUI {
    @Dependency
    List<? extends GenType> stimTypes;
    @Dependency
    NAFCBlockGen blockgen;
    @Dependency
    GenType defaultStimType;

    private static JPanel centerPanel;
    private static final DefaultListModel<String> listModel = new DefaultListModel<>();
    private static GenType selectedType;

    public static void main(String[] args) {
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception e) {
            throw new XGLException(e);
        }

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));
        NAFCTrialGeneratorGUI gui = context.getBean(NAFCTrialGeneratorGUI.class);
        gui.generate();
    }

    public void generate() {
        LinkedHashMap<String, GenType> labelsForStimTypes = new LinkedHashMap<>();
        for (GenType stimType : stimTypes) {
            labelsForStimTypes.put(stimType.getLabel(), stimType);
        }
//        defaultStimType = labelsForStimTypes.get("RandProcedural");
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

        stimTypeDropdown.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                String selectedLabel = (String) stimTypeDropdown.getSelectedItem();
                selectedType = labelsForStimTypes.get(selectedLabel);
                updateParametersUI(selectedType);
            }
        });

        JList<String> trialList = new JList<>(listModel);
        JScrollPane listScrollPane = new JScrollPane(trialList);

        trialList.addListSelectionListener(new ListSelectionListener() {
            @Override
            public void valueChanged(ListSelectionEvent e) {
                if (!e.getValueIsAdjusting()) {
                    int selectedIndex = trialList.getSelectedIndex();
                    if (selectedIndex != -1) {
                        selectedType = blockgen.getTypeForBlock(selectedIndex);
                        stimTypeDropdown.setSelectedItem(selectedType.getLabel());
                        selectedType.loadParametersIntoFields(blockgen.getParamsForBlock(selectedIndex));
                    }
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

        addTrialsButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                blockgen.addBlock(selectedType);
                listModel.addElement(selectedType.getInfo());
            }
        });

        generateButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                blockgen.uploadTrialParams();
                blockgen.generate();
                //end program
                System.exit(0);
            }
        });

        removeButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                int selectedIndex = trialList.getSelectedIndex();
                if (selectedIndex != -1) {
                    listModel.remove(selectedIndex);
                    blockgen.removeBlock(selectedIndex);
                }
            }
        });

        editButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                int selectedIndex = trialList.getSelectedIndex();
                if (selectedIndex != -1) {
                    blockgen.editBlock(selectedIndex, selectedType);
                    listModel.set(selectedIndex, selectedType.getInfo());
                }
            }
        });

        frame.getContentPane().add(BorderLayout.NORTH, topPanel);
        frame.getContentPane().add(BorderLayout.WEST, centerPanel);
        frame.getContentPane().add(BorderLayout.CENTER, listScrollPane);
        frame.getContentPane().add(BorderLayout.SOUTH, bottomPanel);
        frame.setVisible(true);

        //Download Trial Params from Database
        Map<GenParameters, String> paramsForGenTypes = blockgen.downloadTrialParams();
        System.out.println(paramsForGenTypes.entrySet());
        if (paramsForGenTypes != null) {
            for (Map.Entry<GenParameters, String> entry : paramsForGenTypes.entrySet()) {
                if (entry.getKey() == null) {
                    continue;
                }
                GenType genType = labelsForStimTypes.get(entry.getValue());
                updateParametersUI(genType);
                System.out.println("Entry Key: " + entry.getKey());
                genType.loadParametersIntoFields(entry.getKey());
                blockgen.addBlock(genType);
                listModel.addElement(genType.getInfo());
            }
        }
    }

    private static void updateParametersUI(GenType selectedType) {
        centerPanel.removeAll();
        selectedType.addFieldsToPanel(centerPanel);
        centerPanel.revalidate();
        centerPanel.repaint();
    }

    public void setStimTypes(List<? extends GenType> stimTypes) {
        this.stimTypes = stimTypes;
    }

    public void setBlockgen(NAFCBlockGen blockgen) {
        this.blockgen = blockgen;
    }

    public void setDefaultStimType(ProceduralRandGenType defaultStimType) {
        this.defaultStimType = defaultStimType;
    }
}