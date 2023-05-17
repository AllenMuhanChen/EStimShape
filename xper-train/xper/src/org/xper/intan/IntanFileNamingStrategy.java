package org.xper.intan;

import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;

/**
 * @author Allen Chen
 *
 * To make your own NamingStrategy, make a new class that extends this one
 * and implement rename(). The new class should declare
 * the data type with NewFileNamingStrategy<Type>
 */
public abstract class IntanFileNamingStrategy<T> {
    @Dependency
    IntanRecordingController intanRecordingController;

    public abstract void rename(T parameter);

    public IntanRecordingController getIntanController() {
        return intanRecordingController;
    }

    public void setIntanController(IntanRecordingController intanRecordingController) {
        this.intanRecordingController = intanRecordingController;
    }
}