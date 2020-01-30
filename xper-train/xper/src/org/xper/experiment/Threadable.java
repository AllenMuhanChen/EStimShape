package org.xper.experiment;

public interface Threadable extends Stoppable, Runnable {
	public boolean isRunning();

	public void start();
}
