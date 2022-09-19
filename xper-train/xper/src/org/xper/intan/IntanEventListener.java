package org.xper.intan;

import org.xper.Dependency;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.listener.ExperimentEventListener;

public class IntanEventListener implements TrialEventListener, ExperimentEventListener {
    @Dependency
    IntanController intanController;

    private boolean intanPresent = false;

    @Override
    public void experimentStart(long timestamp) {
        try {
            intanController.connect();
            intanPresent = true;
        } catch (Exception e){
            System.err.println("Could not connect to Intan");
        }
    }

    @Override
    public void experimentStop(long timestamp) {
        if (intanPresent)
            intanController.disconnect();
    }

    @Override
    public void trialInit(long timestamp, TrialContext context) {
        if (intanPresent)
            intanController.record();
    }

    @Override
    public void trialStop(long timestamp, TrialContext context) {
        if (intanPresent)
            intanController.stop();
    }

    @Override
    public void trialStart(long timestamp, TrialContext context) {

    }

    @Override
    public void fixationPointOn(long timestamp, TrialContext context) {

    }

    @Override
    public void initialEyeInFail(long timestamp, TrialContext context) {

    }

    @Override
    public void initialEyeInSucceed(long timestamp, TrialContext context) {

    }

    @Override
    public void eyeInHoldFail(long timestamp, TrialContext context) {

    }

    @Override
    public void fixationSucceed(long timestamp, TrialContext context) {

    }

    @Override
    public void eyeInBreak(long timestamp, TrialContext context) {

    }

    @Override
    public void trialComplete(long timestamp, TrialContext context) {

    }



}
