package org.xper.intan;

import org.xper.classic.vo.TrialContext;

public class TaskIdFileNamingStrategy extends IntanFileNamingStrategy{

    @Override
    public void rename(TrialContext context) {
        long taskId = context.getCurrentTask().getTaskId();
        intanController.setBaseFilename(Long.toString(taskId));
    }
}
