package org.xper.console;

import org.xper.db.vo.BehMsgEntry;

public interface ExperimentMessageHandler {
	public boolean handleMessage (BehMsgEntry msg);
}
