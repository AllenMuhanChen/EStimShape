package org.xper.experiment.listener;

import org.xper.Dependency;
import org.xper.rfplot.RFPlotTaskDataSource;

public class RFPlotTaskDataSourceController implements ExperimentEventListener {
	
	@Dependency
	RFPlotTaskDataSource taskDataSource;

	public void experimentStart(long timestamp) {
		taskDataSource.start();
	}

	public void experimentStop(long timestamp) {
		taskDataSource.stop();
	}

	public RFPlotTaskDataSource getTaskDataSource() {
		return taskDataSource;
	}

	public void setTaskDataSource(RFPlotTaskDataSource taskDataSource) {
		this.taskDataSource = taskDataSource;
	}

	
}
