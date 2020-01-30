package org.xper.eye.vo;

import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class EyeZeroMessage {
	long timestamp;
	String id;
	Coordinates2D zero;
	
	static XStream xstream = new XStream();

	static {
		xstream.alias("EyeZeroMessage", EyeZeroMessage.class);
		xstream.alias("Coordinates2D", Coordinates2D.class);
	}
	
	public static EyeZeroMessage fromXml (String xml) {
		return (EyeZeroMessage)xstream.fromXML(xml);
	}
	
	public static String toXml (EyeZeroMessage msg) {
		return xstream.toXML(msg);
	}
	
	public EyeZeroMessage() {}
	
	public EyeZeroMessage(long timestamp, String id, Coordinates2D zero) {
		super();
		this.timestamp = timestamp;
		this.id = id;
		this.zero = zero;
	}
	
	public String getId() {
		return id;
	}
	public void setId(String id) {
		this.id = id;
	}
	public long getTimestamp() {
		return timestamp;
	}
	public void setTimestamp(long timestamp) {
		this.timestamp = timestamp;
	}
	public Coordinates2D getZero() {
		return zero;
	}
	public void setZero(Coordinates2D zero) {
		this.zero = zero;
	}
}
