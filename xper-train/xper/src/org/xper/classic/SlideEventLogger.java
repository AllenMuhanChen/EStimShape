package org.xper.classic;

import java.sql.Timestamp;

import org.apache.log4j.Logger;

public class SlideEventLogger implements SlideEventListener {
	static Logger logger = Logger.getLogger(SlideEventLogger.class);
	
	long total = 0;
	long n = 0;
	long max = 0;
	
	long slideOnTimestamp;

	public void slideOff(int index, long timestamp, int frameCount) {
		long t = timestamp - slideOnTimestamp;
		total += t;
		n ++;
		if (t > max) max = t;
		log("slideOff", index, timestamp);
		logger.info( frameCount + " physical frames drawn. Time " + (t/1000) + " ms. Max " + (max/1000) + " Avg " + (total/n/1000));
	}

	public void slideOn(int index, long timestamp) {
		slideOnTimestamp = timestamp;
		log("slideOn", index, timestamp);
	}

	protected void log(String event, int i, long timestamp) {
		logger.info(event + "(" + i + "): "
				+ new Timestamp(timestamp/1000).toString());
	}
}
