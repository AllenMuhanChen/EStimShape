package org.xper.sach.util;

import java.io.IOException;
import java.util.List;

public class BlenderRunnable implements Runnable {
	List<String> args;
	boolean doWaitFor = false;
	
	@Override
	public void run() {
		try {
			ProcessBuilder builder = new ProcessBuilder(args);
			Process process = builder.start();
			if (doWaitFor)
				process.waitFor();
			
		} catch (IOException e) {
			e.printStackTrace();
		} catch (InterruptedException e) {
			e.printStackTrace();
		}
	}
	
	public void setArgs(List<String> args) {
		this.args = args;
	}
	
	public void setDoWaitFor(boolean doWaitFor) {
		this.doWaitFor = doWaitFor;
	}

}
