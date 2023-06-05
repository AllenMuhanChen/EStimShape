package org.xper.fixtrain;

import java.util.concurrent.atomic.AtomicReference;

import org.apache.log4j.Logger;
import org.xper.classic.TrialExperimentMessageHandler;
import org.xper.db.vo.BehMsgEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.vo.EyeWindow;

public class FixTrainMessageHandler extends TrialExperimentMessageHandler {
    static Logger logger = Logger.getLogger(FixTrainMessageHandler.class);

    AtomicReference<Coordinates2D> fixationPosition = new AtomicReference<Coordinates2D>();

    public boolean handleMessage(BehMsgEntry msg) {
        if ("EyeDeviceMessage".equals(msg.getType())) {
            handleEyeDeviceMessage(msg);
            return true;
        } else if ("FixationPointOn".equals(msg.getType())) {
            fixationOn.set(true);
            return true;
        } else if ("FixationSucceed".equals(msg.getType())){

            return true;
        } else if ("EyeInBreak".equals(msg.getType()) ||
                "EyeInHoldFail".equals(msg.getType()) ||
                "InitialEyeInFail".equals(msg.getType()) ||
                "TrialComplete".equals(msg.getType())) {
            fixationOn.set(false);
            inTrial.set(false);
            return true;
        } else if ("EyeWindowMessage".equals(msg.getType())) {
            handleEyeWindowMessage(msg);
            return true;
        } else if ("EyeZeroMessage".equals(msg.getType())) {
            handleEyeZeroMessage(msg);
            return true;
        } else if ("TrialStatistics".equals(msg.getType())) {
            handleTrialStatistics(msg);
            return true;
        } else if ("TrialInit".equals(msg.getType())) {
            inTrial.set(true);
            return true;
        } else if ("TrialStop".equals(msg.getType())) {
            return true;
        } else if ("EyeInEvent".equals(msg.getType())) {
            eyeIn.set(true);
            return true;
        } else if ("EyeOutEvent".equals(msg.getType())) {
            eyeIn.set(false);
            return true;
        }
        else if ("CalibrationPointSetup".equals(msg.getType())) {
            FixTrainCalibrationPointSetupMessage m = FixTrainCalibrationPointSetupMessage.fromXml(msg.getMsg());
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