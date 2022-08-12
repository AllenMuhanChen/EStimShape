package org.xper.eye.listener;

import java.sql.Timestamp;
import java.util.Map;

import org.apache.log4j.Logger;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.vo.EyePosition;

public class EyeEventLogger implements EyeEventListener {
	static Logger logger = Logger.getLogger(EyeEventLogger.class);

	public void eyeIn(EyePosition eyePos, long timestamp) {
		log("eyeIn", eyePos, timestamp);
	}

	public void eyeOut(EyePosition eyePos, long timestamp) {
		log("eyeOut", eyePos, timestamp);
	}

	protected void log(String event, EyePosition eyePos, long timestamp) {
		StringBuffer buf = new StringBuffer();
		buf.append(event + ": ");
		buf.append(new Timestamp(timestamp/1000).toString());
		for (Map.Entry<String, Coordinates2D> e : eyePos.getPos().entrySet()) {
			String dev = e.getKey();
			Coordinates2D pos = e.getValue();
			buf.append (" " + dev);
			buf.append("<" + pos.getX() + "," + pos.getY() + ">");
		}
		logger.info(buf.toString());
	}
}
