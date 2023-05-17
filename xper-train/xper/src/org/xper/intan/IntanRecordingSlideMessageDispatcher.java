package org.xper.intan;

import org.xper.Dependency;
import org.xper.classic.SlideEventListener;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.exception.RemoteException;
import org.xper.experiment.listener.ExperimentEventListener;

/**
 * Controls what trial, slide and experiment events trigger what methods in IntanRecordingController.
 *
 * experimentStart: connect to Intan
 * trialInit: start recording (starting a new data file)
 * slideOn: write a liveNote to Intan to tell what the taskId is
 * trialStop: stop recording
 * experimentStop: disconnect from Intan
 */
public class IntanRecordingSlideMessageDispatcher implements SlideEventListener, TrialEventListener, ExperimentEventListener{

    @Dependency
    private
    IntanRecordingController intanController;

    @Dependency
    IntanFileNamingStrategy<Object> fileNamingStrategy;

    private boolean connected = false;

    @Override
    public void experimentStart(long timestamp) {
        tryConnection();
    }


    @Override
    public void trialInit(long timestamp, TrialContext context) {
        if (connected) {
            long trialName = context.getCurrentTask().getTaskId();
            fileNamingStrategy.rename(trialName);
            getIntanController().record();
        }
    }

    @Override
    public void slideOn(int index, long timestamp, long taskId) {
        if (connected){
            String note = Long.toString(taskId);
            getIntanController().writeNote(note);
        }
    }

    @Override
    public void trialStop(long timestamp, TrialContext context) {
        if (connected)
            getIntanController().stopRecording();
    }


    @Override
    public void experimentStop(long timestamp) {
        if (connected) {
            getIntanController().stop();
            getIntanController().disconnect();
        }
        connected = false;
    }

    private void tryConnection() {
        try {
            getIntanController().connect();
            connected = true;
        } catch (RemoteException e){
            System.err.println("Could not connect to Intan, disabling Intan functionality");
            connected = false;
        }
    }


    @Override
    public void slideOff(int index, long timestamp, int frameCount, long taskId) {

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
        return intanController;
    }

    public void setIntanController(IntanRecordingController intanRecordingController) {
        this.intanController = intanRecordingController;
    }

    public IntanFileNamingStrategy<Object> getFileNamingStrategy() {
        return fileNamingStrategy;
    }

    public void setFileNamingStrategy(IntanFileNamingStrategy<Object> fileNamingStrategy) {
        this.fileNamingStrategy = fileNamingStrategy;
    }

}