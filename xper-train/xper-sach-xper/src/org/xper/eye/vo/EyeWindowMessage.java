package org.xper.eye.vo;

import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class EyeWindowMessage {
	long timestamp;
	Coordinates2D center;
	double size;
	
	static XStream xstream = new XStream();

	static {
		xstream.alias("EyeWindowMessage", EyeWindowMessage.class);
		xstream.alias("Coordinates2D", Coordinates2D.class);
	}
	
	public static EyeWindowMessage fromXml (String xml) {
		return (EyeWindowMessage)xstream.fromXML(xml);
	}
	
	public static String toXml (EyeWindowMessage msg) {
		return xstream.toXML(msg);
	}
	
	public EyeWindowMessage() {}
	
	public EyeWindowMessage(long timestamp, Coordinates2D center, double size) {
		super();
		this.timestamp = timestamp;
		this.center = center;
		this.size = size;
	}
	public Coordinates2D getCenter() {
		return center;
	}
	public void setCenter(Coordinates2D center) {
		this.center = center;
	}
	public double getSize() {
		return size;
	}
	public void setSize(double size) {
		this.size = size;
	}
	public long getTimestamp() {
		return timestamp;
	}
	public void setTimestamp(long timestamp) {
		this.timestamp = timestamp;
	}
}
