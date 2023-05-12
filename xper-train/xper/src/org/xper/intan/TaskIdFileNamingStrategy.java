package org.xper.intan;

import org.xper.classic.vo.TrialContext;

/**
 * @author Allen Chen
 */
public class TaskIdFileNamingStrategy extends IntanFileNamingStrategy{

    @Override
    public void rename(TrialContext context) {
        long taskId = context.getCurrentTask().getTaskId();
        intanRecordingController.setBaseFilename(Long.toString(taskId));
    }
}