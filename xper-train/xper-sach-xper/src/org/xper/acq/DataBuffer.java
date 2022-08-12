package org.xper.acq;

public interface DataBuffer {
	public void startSession ();
	public void stopSession ();
	
	public void put (short channel, int sampleInd, double value);
}
