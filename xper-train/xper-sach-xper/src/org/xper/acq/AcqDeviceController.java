package org.xper.acq;

public interface AcqDeviceController {
	public void connect ();
	public void disconnect ();
	
	public void start();
	public void stop();
	
	public boolean isRunning();
}
