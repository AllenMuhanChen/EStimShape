package org.xper.allen.db.vo;

import org.xper.allen.specs.StimSpec;
import org.xper.db.vo.StimSpecEntry;

import com.thoughtworks.xstream.XStream;

public class AllenStimSpecEntry extends StimSpecEntry{

	public StimSpec genStimSpec() {
		StimSpec ss = StimSpec.fromXml(getSpec());
		return ss;
	}
	
	transient static XStream s;

	static {
		s = new XStream();
		s.alias("StimSpec", AllenStimSpecEntry.class);
	}

	public String toXml() {
		return AllenStimSpecEntry.toXml(this);
	}

	public static String toXml(AllenStimSpecEntry spec) {
		return s.toXML(spec);
	}

	public static AllenStimSpecEntry fromXml(String xml) {
		AllenStimSpecEntry g = (AllenStimSpecEntry) s.fromXML(xml);
		return g;
	}
}
