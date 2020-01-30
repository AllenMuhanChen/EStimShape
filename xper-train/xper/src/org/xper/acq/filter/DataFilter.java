package org.xper.acq.filter;

public interface DataFilter {
	/**
	 * 
	 * @param chan
	 * @param sampleIndex
	 * @param startSampleIndex of the session
	 * @param value
	 */
	public void filter(short chan, int sampleIndex, int startSampleIndex, double value);
	
	/**
	 * This resets the filter. Calling it multiple time should have no side effects.
	 */
	public void init ();
}
