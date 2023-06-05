package org.xper.fixtrain;

import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Coordinates2D;
import org.xper.fixcal.FixCalMessageDispatcher;
import org.xper.fixtrain.drawing.FixTrainDrawable;

import java.util.Map;

public class FixTrainMessageDispatcher extends FixCalMessageDispatcher {

    @Dependency
    Map<String, FixTrainDrawable<?>> fixTrainObjectMap;

    @Override
    public void calibrationPointSetup(long timestamp, Coordinates2D pos,
            TrialContext context) {
        String fixTrainStimSpec = context.getCurrentTask().getStimSpec();
        FixTrainStimSpec stim = FixTrainStimSpec.fromXml(fixTrainStimSpec);
        String stimSpec = stim.getStimSpec();
        String stimClass = stim.getStimClass();

        FixTrainDrawable<?> drawable = fixTrainObjectMap.get(stimClass);
        drawable.setSpec(stimSpec);
        String size = drawable.getSize().toString();

        enqueue(timestamp, "CalibrationPointSetup", FixTrainCalibrationPointSetupMessage
                .toXml(new FixTrainCalibrationPointSetupMessage(pos, stimSpec, stimClass, size)));
    }

    public Map<String, FixTrainDrawable<?>> getFixTrainObjectMap() {
        return fixTrainObjectMap;
    }

    public void setFixTrainObjectMap(Map<String, FixTrainDrawable<?>> fixTrainObjectMap) {
        this.fixTrainObjectMap = fixTrainObjectMap;
    }

}