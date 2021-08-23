package org.xper.allen.nafc;

import org.xper.allen.saccade.console.SaccadeTargetMessage;
import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class NAFCSampleMessage {
	long stimObjDataId;
	
	public NAFCSampleMessage(long stimObjDataId) {
		super();
		this.stimObjDataId = stimObjDataId;
	}


	public long getStimObjDataId() {
		return stimObjDataId;
	}

	public void setStimObjDataId(long stimObjDataId) {
		this.stimObjDataId = stimObjDataId;
	}
	
	transient static XStream s = new XStream();
	
	static {
		s.alias("TwoACSampleMessage", SaccadeTargetMessage.class);
		s.alias("Coordinates2D", Coordinates2D.class);
	}
	
	public static String toXml(NAFCSampleMessage msg) {
		return s.toXML(msg);
	}
	
	public String toXml() {
		return s.toXML(this);
	}
	
	public static NAFCSampleMessage fromXml(String xml) {
		return (NAFCSampleMessage)s.fromXML(xml);
	}
	
}
