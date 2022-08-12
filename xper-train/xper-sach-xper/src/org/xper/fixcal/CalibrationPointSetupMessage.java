package org.xper.fixcal;

import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class CalibrationPointSetupMessage {
	Coordinates2D fixationPosition;
	
	static XStream xstream = new XStream();

	static {
		xstream.alias("CalibrationPointSetupMessage", CalibrationPointSetupMessage.class);
	}

	public CalibrationPointSetupMessage(Coordinates2D fixationPosition) {
		super();
		this.fixationPosition = fixationPosition;
	}

	public Coordinates2D getFixationPosition() {
		return fixationPosition;
	}

	public void setFixationPosition(Coordinates2D fixationPosition) {
		this.fixationPosition = fixationPosition;
	}	
	
	public static CalibrationPointSetupMessage fromXml (String xml) {
		return (CalibrationPointSetupMessage)xstream.fromXML(xml);
	}
	
	public static String toXml (CalibrationPointSetupMessage msg) {
		return xstream.toXML(msg);
	}
}
