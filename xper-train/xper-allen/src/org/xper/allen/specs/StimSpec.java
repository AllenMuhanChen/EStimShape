package org.xper.allen.specs;

import org.xper.allen.config.AllenDbUtil;

import com.thoughtworks.xstream.XStream;

public class StimSpec {
	long[] stimObjData;
	long[] eStimObjData;

	
	public StimSpec(long[] stimObjIds, long[] estimIds) {
		stimObjIds = new long[stimObjIds.length];
		estimIds = new long[estimIds.length];
	}
	
	public StimSpec() {
	//Default Constructor	
	}
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("StimSpec", StimSpec.class);
	}
	
	public static String toXml (StimSpec spec) {
		return s.toXML(spec);
	}
	
	public String toXml() {
		return StimSpec.toXml(this);
	}
	
	public static StimSpec fromXml (String xml) {
		StimSpec ss = (StimSpec)s.fromXML(xml);
		return ss;
	}

	public long[] getStimObjData() {
		return stimObjData;
	}

	public void setStimObjData(long[] stimObjData) {
		this.stimObjData = stimObjData;
	}

	public long[] geteStimObjData() {
		return eStimObjData;
	}

	public void seteStimObjData(long[] eStimObjData) {
		this.eStimObjData = eStimObjData;
	}

}
