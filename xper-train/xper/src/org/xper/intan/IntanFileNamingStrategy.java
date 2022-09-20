package org.xper.intan;

import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;

public abstract class IntanFileNamingStrategy {
    @Dependency
    IntanController intanController;

    private String savePath;
    private String baseFilename;

    protected abstract void generatePath(TrialContext context);
    protected abstract void generateBaseFilename(TrialContext context);

    public void rename(TrialContext context){
        generatePath(context);
        generateBaseFilename(context);

        intanController.setSavePath(savePath);
        intanController.setBaseFilename(baseFilename);
    }

}
