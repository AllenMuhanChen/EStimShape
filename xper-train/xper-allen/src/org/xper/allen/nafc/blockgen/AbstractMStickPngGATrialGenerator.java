package org.xper.allen.nafc.blockgen;

import org.xper.Dependency;

public class AbstractMStickPngGATrialGenerator extends AbstractTrialGenerator{

    @Dependency
    protected String generatorPngPath;
    @Dependency
    protected String experimentPngPath;
    @Dependency
    protected String generatorSpecPath;

    @Override
    protected void addTrials() {

    }
}
