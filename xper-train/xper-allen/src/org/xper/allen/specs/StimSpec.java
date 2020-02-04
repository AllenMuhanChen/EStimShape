package org.xper.allen.specs;

import org.xper.allen.config.AllenDbUtil;

import com.thoughtworks.xstream.XStream;

public class StimSpec {
	long estimIds[];
	long stimObjIds[];

	
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
	
	public StimSpec fromXml (String xml) {
		StimSpec ss = (StimSpec)s.fromXML(xml);
		return ss;
	}

	public long[] getEstimIds() {
		return estimIds;
	}

	public void setEstimIds(long[] estimIds) {
		this.estimIds = estimIds;
	}

	public long[] getStimObjIds() {
		return stimObjIds;
	}

	public void setStimObjId(long[] stimObjId) {
		this.stimObjIds = stimObjId;
	}
}
