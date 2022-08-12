package org.xper.eye.vo;

import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class EyeDeviceMessage {
	long timestamp;
	String id;
	Coordinates2D volt;
	Coordinates2D degree;
	
	public EyeDeviceMessage() {}
	
	public EyeDeviceMessage(long timestamp, String id, Coordinates2D volt, Coordinates2D degree) {
		super();
		this.timestamp = timestamp;
		this.id = id;
		this.volt = volt;
		this.degree = degree;
	}
	
	static XStream xstream = new XStream();
	
	static {
		xstream.alias("EyeDeviceMessage", EyeDeviceMessage.class);
		xstream.alias("Coordinates2D", Coordinates2D.class);
	}
	
	public static EyeDeviceMessage fromXml (String xml) {
		return (EyeDeviceMessage)xstream.fromXML(xml);
	}
	
	public static String toXml (EyeDeviceMessage msg) {
		return xstream.toXML(msg);
	}
	public Coordinates2D getDegree() {
		return degree;
	}
	public void setDegree(Coordinates2D degree) {
		this.degree = degree;
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
	public Coordinates2D getVolt() {
		return volt;
	}
	public void setVolt(Coordinates2D volt) {
		this.volt = volt;
	}
}
