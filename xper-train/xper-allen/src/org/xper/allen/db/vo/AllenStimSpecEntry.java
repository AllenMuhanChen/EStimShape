package org.xper.allen.db.vo;

import org.xper.allen.specs.StimSpec;
import org.xper.db.vo.StimSpecEntry;

public class AllenStimSpecEntry extends StimSpecEntry{
	/**
	 * It's the timestamp in microseconds.
	 */
	long stimId;
	/**
	 * Encoded as XML string.
	 */
	String spec;

	public StimSpec genStimSpec() {
		StimSpec ss = new StimSpec();
		ss.fromXml(spec);
		return ss;
	}
}
