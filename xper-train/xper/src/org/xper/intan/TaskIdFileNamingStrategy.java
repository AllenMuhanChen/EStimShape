package org.xper.intan;

import org.xper.classic.vo.TrialContext;

/**
 * @author Allen Chen
 */
public class TaskIdFileNamingStrategy extends IntanFileNamingStrategy<Long>{

    @Override
    public void rename(Long parameter) {
        intanRecordingController.setBaseFilename(parameter.toString());
    }
}