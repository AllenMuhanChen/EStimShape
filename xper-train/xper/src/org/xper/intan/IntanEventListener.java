package org.xper.intan;

import org.xper.Dependency;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.listener.ExperimentEventListener;

public class IntanEventListener implements TrialEventListener, ExperimentEventListener {
    @Dependency
    IntanController intanController;

    @Override
    public void experimentStart(long timestamp) {
        intanController.connect();
    }

    @Override
    public void experimentStop(long timestamp) {
        intanController.stop();
    }

    @Override
    public void trialInit(long timestamp, TrialContext context) {
        intanController.record();
    }

    @Override
    public void trialStop(long timestamp, TrialContext context) {
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
