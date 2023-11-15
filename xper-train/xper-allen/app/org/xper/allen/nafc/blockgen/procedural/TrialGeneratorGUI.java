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
    private static JPanel centerPanel;
    private static DefaultListModel<String> listModel = new DefaultListModel<>();
    private static String defaultStimType = "RandStim";
    private static String selectedType = defaultStimType;
    private static RandStimModel randStimModel;

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

        randStimModel = new RandStimModel(blockgen);
        String[] stimTypes = {"RandStim", "MockStim", "OtherStimType2"};
        JComboBox<String> stimTypeDropdown = new JComboBox<>(stimTypes);
        topPanel.add(stimTypeLabel);
        topPanel.add(stimTypeDropdown);

        centerPanel = new JPanel(new GridLayout(0, 2));
//        initializeParameterFields();
        updateParametersUI(defaultStimType);

        stimTypeDropdown.addActionListener(e -> {
            selectedType = (String) stimTypeDropdown.getSelectedItem();
            updateParametersUI(selectedType);
        });

        JList<String> trialList = new JList<>(listModel);
        JScrollPane listScrollPane = new JScrollPane(trialList);
        listScrollPane.setPreferredSize(new Dimension(400, 100));

        trialList.addListSelectionListener(e -> {
            if (!e.getValueIsAdjusting()) {
                int selectedIndex = trialList.getSelectedIndex();
                if (selectedIndex != -1) {
                    if ("RandStim".equals(stimTypeDropdown.getSelectedItem())) {
                        ProceduralStim.ProceduralStimParameters parameters = blockgen.getBlockParameters(selectedIndex);
                        int numTrials = blockgen.getNumTrials(selectedIndex);
                        randStimModel.loadParametersIntoFields(parameters, numTrials);
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

        addTrialsButton.addActionListener(e -> {
            if ("RandStim".equals(stimTypeDropdown.getSelectedItem())) {
                ProceduralStim.ProceduralStimParameters proceduralStimParameters =
                        randStimModel.getProceduralStimParameters();
                int numTrials = randStimModel.getNumTrials();

                blockgen.addBlock(randStimModel.genTrials(proceduralStimParameters, numTrials));
                listModel.addElement("Type: " + selectedType + ", Trials: " + numTrials);
            }
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
                if ("RandStim".equals(stimTypeDropdown.getSelectedItem())) {
                    ProceduralStim.ProceduralStimParameters parameters = randStimModel.getProceduralStimParameters();
                    int numTrials = randStimModel.getNumTrials();
                    blockgen.editBlock(selectedIndex, randStimModel.genTrials(parameters, numTrials));
                    listModel.set(selectedIndex, "Type: " + selectedType + ", Trials: " + numTrials);
                }
            }


        });

        frame.getContentPane().add(BorderLayout.NORTH, topPanel);
        frame.getContentPane().add(BorderLayout.CENTER, centerPanel);
        frame.getContentPane().add(BorderLayout.EAST, listScrollPane);
        frame.getContentPane().add(BorderLayout.SOUTH, bottomPanel);
        frame.setVisible(true);
    }


    private static void updateParametersUI(String stimType) {
        centerPanel.removeAll();
        if ("RandStim".equals(stimType)){
            randStimModel.addParameterFieldsToPanel(centerPanel);
        }
        centerPanel.revalidate();
        centerPanel.repaint();
    }
}