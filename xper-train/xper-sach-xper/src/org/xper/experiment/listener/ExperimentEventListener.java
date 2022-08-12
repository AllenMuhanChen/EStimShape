package org.xper.experiment.listener;

public interface ExperimentEventListener {
	/**
	 * 
	 * @param timestamp in microseconds
	 */
	public void experimentStart (long timestamp);
	public void experimentStop (long timestamp);
}
