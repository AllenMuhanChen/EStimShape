package org.xper.experiment;




public interface TaskDataSource {
	/**
	 * @return null or valid experiment task.
	 */
	public ExperimentTask getNextTask ();

	public void ungetTask(ExperimentTask t);
}
