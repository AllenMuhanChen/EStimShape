package org.xper.eye.vo;

import java.util.Map;

import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class EyePosition {
	Map<String, Coordinates2D> pos;
	
	static XStream xstream = new XStream();

	static {
		xstream.alias("EyePosition", EyePosition.class);
		xstream.alias("Coordinates2D", Coordinates2D.class);
	}
	
	public static EyePosition fromXml (String xml) {
		return (EyePosition)xstream.fromXML(xml);
	}
	
	public static String toXml (EyePosition msg) {
		return xstream.toXML(msg);
	}

	public Map<String, Coordinates2D> getPos() {
		return pos;
	}

	public void setPos(Map<String, Coordinates2D> pos) {
		this.pos = pos;
	}

	public EyePosition(Map<String, Coordinates2D> pos) {
		super();
		this.pos = pos;
	}
}
