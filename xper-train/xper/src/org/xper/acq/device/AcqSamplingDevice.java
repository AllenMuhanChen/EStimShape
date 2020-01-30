package org.xper.acq.device;

public interface AcqSamplingDevice {
	/**
	 * Get data for a specific channel.
	 * @param channel
	 * @return voltage
	 */
	public double getData(int channel);
	
	/**
	 * 
	 * @return time stamp of the scan in microseconds
	 */
	public long scan ();
}
