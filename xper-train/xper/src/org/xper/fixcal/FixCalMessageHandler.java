package org.xper.fixcal;

import java.util.concurrent.atomic.AtomicReference;

import org.apache.log4j.Logger;
import org.xper.classic.TrialExperimentMessageHandler;
import org.xper.db.vo.BehMsgEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.vo.EyeWindow;

public class FixCalMessageHandler extends TrialExperimentMessageHandler {
	static Logger logger = Logger.getLogger(FixCalMessageHandler.class);
	
	AtomicReference<Coordinates2D> fixationPosition = new AtomicReference<Coordinates2D>();
	
	public boolean handleMessage(BehMsgEntry msg) {
		if(super.handleMessage(msg)) {
			return true;
		}
		if ("CalibrationPointSetup".equals(msg.getType())) {
			CalibrationPointSetupMessage m = CalibrationPointSetupMessage.fromXml(msg.getMsg());
			Coordinates2D pos = m.getFixationPosition();
			fixationPosition.set(pos);

			double size = getEyeWindow().getSize();
			setEyeWindow(new EyeWindow(pos, size));
			
			if (logger.isDebugEnabled()) {
				logger.debug("Fixation position: " + pos.getX() + ", " + pos.getY());
			}
			return true;
		} else {
			return false;
		}
	}

	public Coordinates2D getFixationPosition() {
		return fixationPosition.get();
	}

	public void setFixationPosition(Coordinates2D fixationPosition) {
		this.fixationPosition.set(fixationPosition);
	}
}
