package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.NAFCStim;

import javax.swing.*;
import javax.swing.event.DocumentEvent;
import javax.swing.event.DocumentListener;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.BiConsumer;

/**
 * A new GenType needs a specific:
 * 1. Label.
 * 2. genTrials()
 * 3. initFields() that ADDS the new fields to labelsForFields and defaultsForFields
 * 4. loadParametersIntoFields()
 * 5. readFromFields()
 * @param <T>
 */
public abstract class GenType<T extends GenParameters> {

    protected Map<JTextField, String> labelsForFields;
    protected Map<JTextField, String> defaultsForFields;

    protected final Set<JTextField> modifiedFields = new HashSet<>();
    protected boolean suppressDirtyTracking = false;

    public void setSuppressDirtyTracking(boolean suppress) {
        this.suppressDirtyTracking = suppress;
    }

    public void clearModifiedFields() {
        modifiedFields.clear();
    }

    /** Returns label -> current text for each field the user modified since last clear. */
    public Map<String, String> getModifiedFieldValues() {
        Map<String, String> result = new LinkedHashMap<>();
        if (labelsForFields == null) return result;
        for (JTextField f : modifiedFields) {
            String label = labelsForFields.get(f);
            if (label != null) result.put(label, f.getText());
        }
        return result;
    }

    /** Returns label -> field for the current field set. */
    public Map<String, JTextField> getFieldsByLabel() {
        Map<String, JTextField> result = new LinkedHashMap<>();
        if (labelsForFields == null) return result;
        labelsForFields.forEach((field, label) -> result.put(label, field));
        return result;
    }

    public abstract String getLabel();

    public Map.Entry<List<NAFCStim>, GenParameters> genBlock(){
        T params = readFromFields();
        List<NAFCStim> block = genTrials(params);
        return new java.util.AbstractMap.SimpleEntry<>(block, params);
    }

    protected abstract List<NAFCStim> genTrials(T genParameters);

    public abstract T readFromFields();


    public abstract void initFields();

    public abstract void loadParametersIntoFields(GenParameters parameters);

    public void addFieldsToPanel(JPanel panel){
        initFields();

        defaultsForFields.forEach(new BiConsumer<JTextField, String>() {
            @Override
            public void accept(JTextField field, String defaultValue) {
                field.setText(defaultValue);
            }
        });

        labelsForFields.forEach(new BiConsumer<JTextField, String>() {
            @Override
            public void accept(JTextField paramField, String label) {
                panel.add(new JLabel(label));
                panel.add(paramField);
            }
        });

        modifiedFields.clear();
        suppressDirtyTracking = false;
        for (final JTextField field : labelsForFields.keySet()) {
            field.getDocument().addDocumentListener(new DocumentListener() {
                @Override public void insertUpdate(DocumentEvent e) { mark(); }
                @Override public void removeUpdate(DocumentEvent e) { mark(); }
                @Override public void changedUpdate(DocumentEvent e) { mark(); }
                private void mark() { if (!suppressDirtyTracking) modifiedFields.add(field); }
            });
        }
    }

    public abstract String getInfo();
}