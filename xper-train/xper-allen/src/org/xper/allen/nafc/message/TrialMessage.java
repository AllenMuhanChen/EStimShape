package org.xper.allen.nafc.message;

import org.xper.allen.saccade.console.SaccadeTargetMessage;
import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class TrialMessage {
	long stimSpecId;
	
	public TrialMessage(long stimSpecId) {
		super();
		this.stimSpecId = stimSpecId;
	}


	public long getStimSpecId() {
		return stimSpecId;
	}

	public void setStimSpecId(long stimObjDataId) {
		this.stimSpecId = stimObjDataId;
	}
	
	transient static XStream s = new XStream();
	
	static {
		s.alias("TrialMessage", TrialMessage.class);
	}
	
	public static String toXml(TrialMessage msg) {
		return s.toXML(msg);
	}
	
	public String toXml() {
		return s.toXML(this);
	}
	
	public static TrialMessage fromXml(String xml) {
		return (TrialMessage)s.fromXML(xml);
	}
	
}
