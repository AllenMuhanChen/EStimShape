package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

import javax.swing.*;
import java.util.List;
import java.util.Map;

public abstract class GenType<T extends GenParameters> {
    protected Map<String, JTextField> namesForFields;


    public abstract String getLabel();

    public Map.Entry<List<NAFCStim>, GenParameters> genBlock(){
        T params = getParameters();
        List<NAFCStim> block = genTrials(params);
        return new java.util.AbstractMap.SimpleEntry<>(block, params);
    }

    protected abstract List<NAFCStim> genTrials(T genParameters);

    public abstract T getParameters();

    public abstract NAFCTrialParameters getTrialParameters();

    public abstract void addParameterFieldsToPanel(JPanel panel);

    public abstract void initializeParameterFields();

    public abstract void loadParametersIntoFields(GenParameters parameters);

    public abstract String getInfo();
}