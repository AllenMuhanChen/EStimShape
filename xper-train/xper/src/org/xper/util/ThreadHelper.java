package org.xper.util;

import java.util.concurrent.atomic.AtomicBoolean;

import org.xper.exception.ThreadException;

public class ThreadHelper {
	String name;
	Runnable runnable;

	/**
	 * We need two signals because, when done is set we need to wait until the
	 * thread stops by testing isRunning.
	 */
	AtomicBoolean done = new AtomicBoolean(false);
	AtomicBoolean isRunning = new AtomicBoolean(false);
	Thread thread;

	public ThreadHelper(String name, Runnable runnable) {
		this.name = name;
		this.runnable = runnable;
	}

	public boolean isRunning() {
		return isRunning.get();
	}

	public boolean isDone() {
		return done.get();
	}

	public void stop() {
		if (!isRunning()) {
			throw new ThreadException("Cannot stop thread. " + name
					+ " is not running.");
		}
		done.set(true);
	}

	public void start() {
		if (isRunning()) {
			throw new ThreadException(
					"Cannot start thread. EyeMonitor is already running.");
		}
		thread = new Thread(runnable);
		thread.start();
		synchronized (this) {
			while (!isRunning()) {
				try {
					this.wait();
				} catch (InterruptedException e) {
				}
			}
		}
	}

	public void started() {
		done.set(false);
		isRunning.set(true);
		synchronized (this) {
			this.notify();
		}
	}

	public void stopped() {
		isRunning.set(false);
	}

	public void join() {
		try {
			if (thread != null && thread.isAlive()) {
				thread.join();
			}
		} catch (InterruptedException e) {
			throw new ThreadException(e);
		}
	}
}
