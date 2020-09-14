package org.xper.allen.blockgen;

import org.xper.Dependency;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.time.TimeUtil;

public class SimpleEStimBlockGen {
	@Dependency
	AllenDbUtil dbUtil;
	@Dependency
	TimeUtil globalTimeUtil;
	@Dependency
	AllenXMLUtil xmlUtil;
}
