package org.xper.experiment.listener;

import org.xper.Dependency;
import org.xper.experiment.DatabaseTaskDataSource;

public class DatabaseTaskDataSourceController implements ExperimentEventListener {
	
	@Dependency
	DatabaseTaskDataSource taskDataSource;

	public void experimentStart(long timestamp) {
		taskDataSource.start();
	}

	public void experimentStop(long timestamp) {
		taskDataSource.stop();
	}

	public DatabaseTaskDataSource getTaskDataSource() {
		return taskDataSource;
	}

	public void setTaskDataSource(DatabaseTaskDataSource taskDataSource) {
		this.taskDataSource = taskDataSource;
	}

	
}
