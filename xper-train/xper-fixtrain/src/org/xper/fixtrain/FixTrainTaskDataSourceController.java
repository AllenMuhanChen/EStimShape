package org.xper.fixtrain;

import org.xper.Dependency;
import org.xper.experiment.listener.ExperimentEventListener;

public class FixTrainTaskDataSourceController implements ExperimentEventListener {

    @Dependency
    FixTrainTaskDataSource taskDataSource;

    @Override
    public void experimentStart(long timestamp) {
        taskDataSource.start();
    }

    @Override
    public void experimentStop(long timestamp) {
        taskDataSource.stop();
    }

    public FixTrainTaskDataSource getTaskDataSource() {
        return taskDataSource;
    }

    public void setTaskDataSource(FixTrainTaskDataSource taskDataSource) {
        this.taskDataSource = taskDataSource;
    }
}