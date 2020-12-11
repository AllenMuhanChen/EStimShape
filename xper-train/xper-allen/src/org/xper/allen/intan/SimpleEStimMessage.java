package org.xper.allen.intan;

import org.xper.allen.console.SaccadeTargetMessage;
import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class SimpleEStimMessage {
	long timestamp;
	Coordinates2D targetPos = new Coordinates2D();
	double targetEyeWindowSize;
	long eStimObjDataId;
	
	public SimpleEStimMessage(long timestamp, Coordinates2D targetPos, double targetEyeWindowSize,
			long eStimObjDataId) {
		super();
		this.timestamp = timestamp;
		this.targetPos = targetPos;
		this.targetEyeWindowSize = targetEyeWindowSize;
		this.eStimObjDataId = eStimObjDataId;
	}
	
	public SimpleEStimMessage() {

	}

	transient static XStream s = new XStream();
	
	static {
		s.alias("SimpleEStimMessage", SimpleEStimMessage.class);
		s.alias("Coordinates2D", Coordinates2D.class);
	}
	
	public static SimpleEStimMessage fromXml(String xml) {
		return (SimpleEStimMessage)s.fromXML(xml);
	}
	
	public static String toXml(SimpleEStimMessage msg) {
		return s.toXML(msg);
	}
	
	public String toXml() {
		return s.toXML(this);
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

	public long geteStimObjDataId() {
		return eStimObjDataId;
	}

	public void seteStimObjDataId(long eStimObjDataId) {
		this.eStimObjDataId = eStimObjDataId;
	}
	

}
