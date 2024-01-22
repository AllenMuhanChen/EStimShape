package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

import javax.swing.*;

public abstract class GenType {

    public abstract String getLabel();

    public abstract NAFCTrialParameters getTrialParameters();

    public abstract void addParameterFieldsToPanel(JPanel panel);

    public abstract void initializeParameterFields();

    public abstract void loadParametersIntoFields(GenParameters parameters);

    public abstract String getInfo();
}