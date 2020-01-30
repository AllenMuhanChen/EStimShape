package org.xper.acq.device;

public interface AcqStreamingDevice {
	
	public void connect();
	
	public void disconnect();

	public void start();

	public void stop();
	
	public double[] scan();
}
