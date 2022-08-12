package org.xper.experiment.mock;

import org.xper.Dependency;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.StimSpecGenerator;
import org.xper.experiment.TaskDataSource;

public class RandomTaskDataSource implements TaskDataSource {
	
	@Dependency
	StimSpecGenerator generator;

	public ExperimentTask getNextTask() {
		ExperimentTask task = new ExperimentTask();
		task.setStimSpec(generator.generateStimSpec()); 
		return task;
	}

	public void ungetTask(ExperimentTask t) {
	}

	public StimSpecGenerator getGenerator() {
		return generator;
	}

	public void setGenerator(StimSpecGenerator generator) {
		this.generator = generator;
	}

}
