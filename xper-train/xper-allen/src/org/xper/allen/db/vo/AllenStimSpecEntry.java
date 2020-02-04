package org.xper.allen.db.vo;

import org.xper.allen.specs.StimSpec;
import org.xper.db.vo.StimSpecEntry;

public class AllenStimSpecEntry extends StimSpecEntry{

	public StimSpec genStimSpec() {
		StimSpec ss = StimSpec.fromXml(getSpec());
		return ss;
	}
}
