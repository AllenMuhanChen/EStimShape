package org.xper.acq;

public interface DataFilterController {
	public void startSession ();
	public void stopSession ();
	
	public void put(double [] data);
}
