package org.xper.intan;

import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;

public abstract class IntanFileNamingStrategy {
    @Dependency
    IntanController intanController;

    public abstract void rename(TrialContext context);

    public IntanController getIntanController() {
        return intanController;
    }

    public void setIntanController(IntanController intanController) {
        this.intanController = intanController;
    }
}
