package org.xper.allen.saccade.console;

import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class SaccadeTargetMessage {
	long timestamp;
	Coordinates2D targetPos = new Coordinates2D();
	double targetEyeWindowSize;
	long stimObjDataId;
	
	public SaccadeTargetMessage(long timestamp, Coordinates2D targetPos, double targetEyeWindowSize, long stimObjDataId) {
		this.timestamp = timestamp;
		this.targetPos = targetPos;
		this.targetEyeWindowSize = targetEyeWindowSize;
		this.stimObjDataId = stimObjDataId;
	}

	public SaccadeTargetMessage() {
		
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
	
	public long getStimObjDataId() {
		return stimObjDataId;
	}

	public void setStimObjDataId(long stimObjDataId) {
		this.stimObjDataId = stimObjDataId;
	}
	
	transient static XStream s = new XStream();
	
	static {
		s.alias("SaccadeTargetMessage", SaccadeTargetMessage.class);
		s.alias("Coordinates2D", Coordinates2D.class);
	}
	
	public static SaccadeTargetMessage fromXml(String xml) {
		return (SaccadeTargetMessage)s.fromXML(xml);
	}
	
	public static String toXml(SaccadeTargetMessage msg) {
		return s.toXML(msg);
	}
	
	public String toXml() {
		return s.toXML(this);
	}


}
