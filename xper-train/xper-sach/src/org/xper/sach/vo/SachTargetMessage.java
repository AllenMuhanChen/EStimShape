package org.xper.sach.vo;

import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class SachTargetMessage {
	long timestamp;
	Coordinates2D targetPos = new Coordinates2D();
	double targetEyeWindowSize;
	
	public SachTargetMessage(long timestamp, Coordinates2D targetPos, double targetEyeWindowSize) {
		super();
		this.timestamp = timestamp;
		this.targetPos = targetPos;
		this.targetEyeWindowSize = targetEyeWindowSize;
	}
	public long getTimestamp() {
		return timestamp;
	}
	public void setTimestamp(long timestamp) {
		this.timestamp = timestamp;
	}
	public Coordinates2D getTargetPos() {
		return targetPos;
	}
	public void setTargetPos(Coordinates2D targetPos) {
		this.targetPos = targetPos;
	}
	public double getTargetEyeWindowSize() {
		return targetEyeWindowSize;
	}
	public void setTargetEyeWindowSize(double targetEyeWindowSize) {
		this.targetEyeWindowSize = targetEyeWindowSize;
	}

	static XStream xstream = new XStream();

	static {
		xstream.alias("SachTargetMessage", SachTargetMessage.class);
		xstream.alias("Coordinates2D", Coordinates2D.class);
	}
	
	public static SachTargetMessage fromXml (String xml) {
		return (SachTargetMessage)xstream.fromXML(xml);
	}
	
	public static String toXml (SachTargetMessage msg) {
		return xstream.toXML(msg);
	}
}
