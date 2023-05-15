package org.xper.intan;

import org.xper.Dependency;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.exception.RemoteException;
import org.xper.experiment.listener.ExperimentEventListener;

/**
 * Controls what trial events and experiment events trigger what events in IntanController.
 */
public class IntanRecordingMessageDispatcher implements TrialEventListener, ExperimentEventListener{

    @Dependency
    IntanRecordingController intanRecordingController;

    @Dependency
    IntanFileNamingStrategy fileNamingStrategy;

    private boolean connected = false;

    @Override
    public void experimentStart(long timestamp) {
        tryConnection();
    }

    private void tryConnection() {
        try {
            intanRecordingController.connect();
            connected = true;
        } catch (RemoteException e){
            System.err.println("Could not connect to Intan, disabling Intan functionality");
            connected = false;
        }
    }

    @Override
    public void experimentStop(long timestamp) {
        if (connected) {
            intanRecordingController.stop();
            intanRecordingController.disconnect();
        }
        connected = false;
    }

    @Override
    public void trialInit(long timestamp, TrialContext context) {
        if (connected) {
            fileNamingStrategy.rename(context);
            intanRecordingController.record();
        }
    }

    @Override
    public void trialStop(long timestamp, TrialContext context) {
        if (connected)
            intanRecordingController.stopRecording();
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

    public IntanRecordingController getIntanController() {
        return intanRecordingController;
    }

    public void setIntanController(IntanRecordingController intanRecordingController) {
        this.intanRecordingController = intanRecordingController;
    }

    public IntanFileNamingStrategy getFileNamingStrategy() {
        return fileNamingStrategy;
    }

    public void setFileNamingStrategy(IntanFileNamingStrategy fileNamingStrategy) {
        this.fileNamingStrategy = fileNamingStrategy;
    }
}