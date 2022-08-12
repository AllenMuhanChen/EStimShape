package org.xper.experiment.mock;

import org.xper.experiment.ExperimentTask;
import org.xper.experiment.TaskDoneCache;

public class NullTaskDoneCache implements TaskDoneCache {

	public void flush() {
	}

	public void put(ExperimentTask task, long timestamp, boolean partial) {
	}

}
