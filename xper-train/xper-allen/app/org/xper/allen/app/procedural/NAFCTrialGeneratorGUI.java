package org.xper.allen.app.procedural;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.nafc.blockgen.procedural.*;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;
import javax.swing.event.TreeSelectionEvent;
import javax.swing.event.TreeSelectionListener;
import javax.swing.tree.DefaultMutableTreeNode;
import javax.swing.tree.DefaultTreeModel;
import javax.swing.tree.TreePath;
import javax.swing.tree.TreeSelectionModel;
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

    private JFrame frame;
    private JPanel centerPanel;
    private GenType selectedType;

    private JTree trialTree;
    private DefaultTreeModel treeModel;
    private DefaultMutableTreeNode treeRoot;

    private JPanel groupingPanel;
    private final List<JComboBox<String>> groupingLevelDropdowns = new ArrayList<>();

    private LinkedHashMap<String, GenType> labelsForStimTypes;
    private JComboBox<String> stimTypeDropdown;

    /** Names of fields available for grouping. */
    private static final String[] GROUPING_FIELDS = {
            "Type",
            "Number of Trials",
            "Noise Chance",
            "Noise Rate",
            "Number of Choices",
            "Number of Random Distractors",
            "Morph Magnitude",
            "Morph Discreteness",
            "Sample Duration",
            "Size",
            "Eye Win Size",
            "Texture Type",
            "isEStimEnabled",
            "eStimSpecId",
            "stimId",
            "compId"
    };

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
        labelsForStimTypes = new LinkedHashMap<>();
        for (GenType stimType : stimTypes) {
            labelsForStimTypes.put(stimType.getLabel(), stimType);
        }
        selectedType = defaultStimType;

        frame = new JFrame("Trial Generator");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setSize(1200, 700);

        JPanel topPanel = new JPanel();
        JLabel stimTypeLabel = new JLabel("Select Stimulus Type:");
        stimTypeDropdown = new JComboBox<>(labelsForStimTypes.keySet().toArray(new String[0]));
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

        // Tree of trials
        treeRoot = new DefaultMutableTreeNode("Trials");
        treeModel = new DefaultTreeModel(treeRoot);
        trialTree = new JTree(treeModel);
        trialTree.getSelectionModel().setSelectionMode(TreeSelectionModel.DISCONTIGUOUS_TREE_SELECTION);
        trialTree.setRootVisible(false);
        trialTree.setShowsRootHandles(true);

        trialTree.addTreeSelectionListener(new TreeSelectionListener() {
            @Override
            public void valueChanged(TreeSelectionEvent e) {
                List<Integer> indices = getSelectedBlockIndices();
                if (indices.size() == 1) {
                    int idx = indices.get(0);
                    GenType type = blockgen.getTypeForBlock(idx);
                    if (type != null) {
                        selectedType = type;
                        stimTypeDropdown.setSelectedItem(type.getLabel());
                        type.setSuppressDirtyTracking(true);
                        type.loadParametersIntoFields(blockgen.getParamsForBlock(idx));
                        type.setSuppressDirtyTracking(false);
                        type.clearModifiedFields();
                    }
                }
            }
        });

        JScrollPane treeScrollPane = new JScrollPane(trialTree);

        // Grouping panel
        groupingPanel = buildGroupingPanel();

        JPanel rightPanel = new JPanel(new BorderLayout());
        rightPanel.add(groupingPanel, BorderLayout.NORTH);
        rightPanel.add(treeScrollPane, BorderLayout.CENTER);

        // Bottom buttons
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
                rebuildTree();
            }
        });

        generateButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                blockgen.uploadTrialParams();
                blockgen.generate();
                System.exit(0);
            }
        });

        removeButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                List<Integer> indices = getSelectedBlockIndices();
                // Remove descending so indices stay valid
                indices.sort(Comparator.reverseOrder());
                for (int idx : indices) {
                    blockgen.removeBlock(idx);
                }
                rebuildTree();
            }
        });

        editButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                editSelected();
            }
        });

        frame.getContentPane().add(BorderLayout.NORTH, topPanel);
        frame.getContentPane().add(BorderLayout.WEST, centerPanel);
        frame.getContentPane().add(BorderLayout.CENTER, rightPanel);
        frame.getContentPane().add(BorderLayout.SOUTH, bottomPanel);
        frame.setVisible(true);

        // Download Trial Params from Database
        Map<GenParameters, String> paramsForGenTypes = blockgen.downloadTrialParams();
        if (paramsForGenTypes != null) {
            for (Map.Entry<GenParameters, String> entry : paramsForGenTypes.entrySet()) {
                if (entry.getKey() == null) {
                    continue;
                }
                GenType genType = labelsForStimTypes.get(entry.getValue());
                updateParametersUI(genType);
                genType.setSuppressDirtyTracking(true);
                genType.loadParametersIntoFields(entry.getKey());
                genType.setSuppressDirtyTracking(false);
                genType.clearModifiedFields();
                blockgen.addBlock(genType);
            }
            rebuildTree();
        }
    }

    private JPanel buildGroupingPanel() {
        JPanel panel = new JPanel(new BorderLayout());
        panel.setBorder(BorderFactory.createTitledBorder("Grouping"));

        final JPanel levelsHolder = new JPanel();
        levelsHolder.setLayout(new BoxLayout(levelsHolder, BoxLayout.Y_AXIS));

        JPanel buttonRow = new JPanel(new FlowLayout(FlowLayout.LEFT));
        JButton addLevelButton = new JButton("Add Group Level");
        JButton applyButton = new JButton("Apply Grouping");
        buttonRow.add(addLevelButton);
        buttonRow.add(applyButton);

        addLevelButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                addGroupLevelRow(levelsHolder);
            }
        });

        applyButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                rebuildTree();
            }
        });

        panel.add(buttonRow, BorderLayout.NORTH);
        panel.add(levelsHolder, BorderLayout.CENTER);
        return panel;
    }

    private void addGroupLevelRow(final JPanel levelsHolder) {
        final JPanel row = new JPanel(new FlowLayout(FlowLayout.LEFT));
        final JComboBox<String> dropdown = new JComboBox<>(GROUPING_FIELDS);
        JButton removeButton = new JButton("Remove");

        row.add(new JLabel("Group by:"));
        row.add(dropdown);
        row.add(removeButton);

        groupingLevelDropdowns.add(dropdown);
        levelsHolder.add(row);
        levelsHolder.revalidate();
        levelsHolder.repaint();

        removeButton.addActionListener(new ActionListener() {
            @Override
            public void actionPerformed(ActionEvent e) {
                groupingLevelDropdowns.remove(dropdown);
                levelsHolder.remove(row);
                levelsHolder.revalidate();
                levelsHolder.repaint();
            }
        });
    }

    private List<String> getGroupingFields() {
        List<String> fields = new ArrayList<>();
        for (JComboBox<String> dd : groupingLevelDropdowns) {
            Object sel = dd.getSelectedItem();
            if (sel != null) fields.add(sel.toString());
        }
        return fields;
    }

    private void rebuildTree() {
        List<String> groupingFields = getGroupingFields();
        treeRoot.removeAllChildren();

        int count = blockgen.getBlockCount();

        for (int i = 0; i < count; i++) {
            GenType type = blockgen.getTypeForBlock(i);
            GenParameters params = blockgen.getParamsForBlock(i);

            DefaultMutableTreeNode current = treeRoot;
            for (String field : groupingFields) {
                String value = getGroupValue(type, params, field);
                String label = field + ": " + value;
                DefaultMutableTreeNode child = findChildByLabel(current, label);
                if (child == null) {
                    child = new DefaultMutableTreeNode(label);
                    current.add(child);
                }
                current = child;
            }
            String leafText = "[" + i + "] " + (type == null ? "?" : type.getInfo());
            current.add(new DefaultMutableTreeNode(new BlockLeaf(i, leafText)));
        }

        treeModel.reload();
        expandAll(trialTree, new TreePath(treeRoot));
    }

    private static DefaultMutableTreeNode findChildByLabel(DefaultMutableTreeNode parent, String label) {
        for (int i = 0; i < parent.getChildCount(); i++) {
            DefaultMutableTreeNode child = (DefaultMutableTreeNode) parent.getChildAt(i);
            if (label.equals(child.getUserObject())) return child;
        }
        return null;
    }

    private static void expandAll(JTree tree, TreePath parent) {
        DefaultMutableTreeNode node = (DefaultMutableTreeNode) parent.getLastPathComponent();
        for (int i = 0; i < node.getChildCount(); i++) {
            DefaultMutableTreeNode child = (DefaultMutableTreeNode) node.getChildAt(i);
            expandAll(tree, parent.pathByAddingChild(child));
        }
        tree.expandPath(parent);
    }

    private List<Integer> getSelectedBlockIndices() {
        List<Integer> indices = new ArrayList<>();
        TreePath[] paths = trialTree.getSelectionPaths();
        if (paths == null) return indices;
        Set<Integer> seen = new HashSet<>();
        for (TreePath p : paths) {
            DefaultMutableTreeNode node = (DefaultMutableTreeNode) p.getLastPathComponent();
            collectLeafIndices(node, indices, seen);
        }
        return indices;
    }

    private static void collectLeafIndices(DefaultMutableTreeNode node, List<Integer> out, Set<Integer> seen) {
        if (node.getUserObject() instanceof BlockLeaf) {
            int idx = ((BlockLeaf) node.getUserObject()).blockIndex;
            if (seen.add(idx)) out.add(idx);
            return;
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            collectLeafIndices((DefaultMutableTreeNode) node.getChildAt(i), out, seen);
        }
    }

    private void editSelected() {
        List<Integer> indices = getSelectedBlockIndices();
        if (indices.isEmpty()) return;

        if (indices.size() == 1) {
            int idx = indices.get(0);
            blockgen.editBlock(idx, selectedType);
            selectedType.clearModifiedFields();
            rebuildTree();
            return;
        }

        // Multi-edit: snapshot modified field values from the currently-displayed type
        Map<String, String> modifiedValues = selectedType.getModifiedFieldValues();
        if (modifiedValues.isEmpty()) {
            JOptionPane.showMessageDialog(frame,
                    "No fields have been modified.\nType new values into fields, then click Edit Selected Trial.",
                    "Nothing to apply",
                    JOptionPane.INFORMATION_MESSAGE);
            return;
        }

        Map<Integer, List<String>> skippedByBlock = new LinkedHashMap<>();
        for (int idx : indices) {
            GenType type = blockgen.getTypeForBlock(idx);
            GenParameters params = blockgen.getParamsForBlock(idx);

            // Fresh fields, populated from existing params
            type.initFields();
            type.setSuppressDirtyTracking(true);
            type.loadParametersIntoFields(params);
            type.setSuppressDirtyTracking(false);

            Map<String, JTextField> fieldsByLabel = type.getFieldsByLabel();
            List<String> missing = new ArrayList<>();
            for (Map.Entry<String, String> entry : modifiedValues.entrySet()) {
                JTextField field = fieldsByLabel.get(entry.getKey());
                if (field == null) {
                    missing.add(entry.getKey());
                } else {
                    field.setText(entry.getValue());
                }
            }
            if (!missing.isEmpty()) {
                skippedByBlock.put(idx, missing);
            }

            blockgen.editBlock(idx, type);
        }

        // Restore UI for the currently-selected type
        updateParametersUI(selectedType);

        if (!skippedByBlock.isEmpty()) {
            StringBuilder msg = new StringBuilder("<html>Some selected trials don't have all the modified parameters:<br><br>");
            for (Map.Entry<Integer, List<String>> e : skippedByBlock.entrySet()) {
                int idx = e.getKey();
                GenType type = blockgen.getTypeForBlock(idx);
                msg.append("Trial [").append(idx).append("] (")
                        .append(type == null ? "?" : type.getLabel())
                        .append("): missing ")
                        .append(String.join(", ", e.getValue()))
                        .append("<br>");
            }
            msg.append("</html>");
            JOptionPane.showMessageDialog(frame, msg.toString(),
                    "Some parameters were skipped", JOptionPane.WARNING_MESSAGE);
        }

        rebuildTree();
    }

    private void updateParametersUI(GenType selectedType) {
        centerPanel.removeAll();
        selectedType.addFieldsToPanel(centerPanel);
        centerPanel.revalidate();
        centerPanel.repaint();
    }

    /** Extracts a value string from a block's GenType/GenParameters for the named grouping field. */
    private static String getGroupValue(GenType type, GenParameters params, String field) {
        if (type == null || params == null) return "n/a";
        try {
            switch (field) {
                case "Type":
                    return type.getLabel();
                case "Number of Trials":
                    return String.valueOf(params.getNumTrials());
                case "isEStimEnabled":
                    if (params instanceof EStimExperimentGenType.EStimExperimentGenParameters) {
                        return String.valueOf(((EStimExperimentGenType.EStimExperimentGenParameters) params).isEStimEnabled);
                    }
                    return "n/a";
                case "eStimSpecId":
                    if (params instanceof EStimExperimentGenType.EStimExperimentGenParameters) {
                        return String.valueOf(((EStimExperimentGenType.EStimExperimentGenParameters) params).eStimSpecId);
                    }
                    return "n/a";
                case "stimId":
                    if (params instanceof EStimExperimentGenType.EStimExperimentGenParameters) {
                        return String.valueOf(((EStimExperimentGenType.EStimExperimentGenParameters) params).stimId);
                    }
                    return "n/a";
                case "compId":
                    if (params instanceof EStimExperimentGenType.EStimExperimentGenParameters) {
                        return String.valueOf(((EStimExperimentGenType.EStimExperimentGenParameters) params).compId);
                    }
                    return "n/a";
                default: {
                    ProceduralStim.ProceduralStimParameters psp = params.getProceduralStimParameters();
                    if (psp == null) return "n/a";
                    switch (field) {
                        case "Noise Chance": return String.valueOf(psp.noiseChance);
                        case "Noise Rate": return String.valueOf(psp.noiseRate);
                        case "Number of Choices": return String.valueOf(psp.numChoices);
                        case "Number of Random Distractors": return String.valueOf(psp.numRandDistractors);
                        case "Morph Magnitude": return String.valueOf(psp.morphMagnitude);
                        case "Morph Discreteness": return String.valueOf(psp.morphDiscreteness);
                        case "Sample Duration": return String.valueOf(psp.getSampleDuration());
                        case "Size": return String.valueOf(psp.getSize());
                        case "Eye Win Size": return String.valueOf(psp.getEyeWinRadius());
                        case "Texture Type": return String.valueOf(psp.textureType);
                        default: return "n/a";
                    }
                }
            }
        } catch (Exception ex) {
            return "n/a";
        }
    }

    private static class BlockLeaf {
        final int blockIndex;
        final String text;

        BlockLeaf(int blockIndex, String text) {
            this.blockIndex = blockIndex;
            this.text = text;
        }

        @Override
        public String toString() {
            return text;
        }
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
