package org.xper.allen.specs;

import com.thoughtworks.xstream.XStream;

public class StimSpec {
	long estimIds[];
	long stimObjId[];
	
	public StimSpec(long[] stimObjIds, long[] estimIds) {
		stimObjIds = new long[stimObjIds.length];
		estimIds = new long[estimIds.length];
	}
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("StimSpec", StimSpec.class);
	}
	
	public static String toXml (StimSpec spec) {
		return s.toXML(spec);
	}
}
