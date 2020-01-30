package org.xper.experiment;


public interface TaskDoneCache {
	public void put(ExperimentTask task, long timestamp, boolean partial);
	public void flush ();
}
