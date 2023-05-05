package org.xper.allen.nafc.experiment;

import org.xper.Dependency;
import org.xper.allen.util.AllenDbUtil;
import org.xper.experiment.Experiment;
import org.xper.eye.EyeMonitor;
import org.xper.time.TimeUtil;
import org.xper.util.EventUtil;
import org.xper.util.ThreadHelper;

public class MockNAFCTrialExperiment extends NAFCTrialExperiment{

    @Override
    protected void startExperiment(TimeUtil timeUtil) {
        threadHelper.started();
        System.out.println("NAFCTrialExperiment started.");
        EventUtil.fireExperimentStartEvent(timeUtil.currentTimeMicros(),
                stateObject.getExperimentEventListeners());
    }

    @Override
    protected void runTrial() {
        try{
            getTrialRunner().runTrial(stateObject, threadHelper);
        } catch (NullPointerException e){
            e.printStackTrace();
            System.out.println("THERE ARE NO MORE TRIALS");
        }
    }
}
