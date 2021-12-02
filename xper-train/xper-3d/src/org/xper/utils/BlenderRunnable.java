package org.xper.utils;

import java.io.IOException;

public class BlenderRunnable implements Runnable {

	@Override
	public void run() {
		try {
			String runStr = "/Applications/Blender.app/Contents/MacOS/blender --background --python /Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectMakePhoto/dbExchange.py -- 180201_r-281_g-1_l-1_s-6"; 
			Runtime.getRuntime().exec(runStr);
		} catch (IOException e) {
			e.printStackTrace();
		}
	}

}
