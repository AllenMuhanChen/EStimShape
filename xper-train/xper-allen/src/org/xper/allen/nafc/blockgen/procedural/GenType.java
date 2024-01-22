package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.NAFCStim;

import javax.swing.*;
import java.util.List;
import java.util.Map;
import java.util.function.BiConsumer;

public abstract class GenType<T extends GenParameters> {

    protected Map<JTextField, String> labelsForFields;
    protected Map<JTextField, String> defaultsForFields;

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
    }

    public abstract String getInfo();
}