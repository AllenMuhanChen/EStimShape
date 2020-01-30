package org.xper.experiment.mock;

import org.xper.experiment.ExperimentTask;
import org.xper.experiment.TaskDataSource;

public class NullTaskDataSource implements TaskDataSource {

	public ExperimentTask getNextTask() {
		return null;
	}

	public void ungetTask(ExperimentTask t) {
	}
}
