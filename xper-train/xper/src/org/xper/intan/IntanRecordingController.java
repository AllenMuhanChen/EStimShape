package org.xper.intan;

import org.xper.Dependency;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.exception.RemoteException;
import org.xper.experiment.listener.ExperimentEventListener;

/**
 * Controls what trial and experiment events trigger what methods in IntanRecordingController.
 *
 * experimentStart: connect to Intan
 * trialInit: start recording (starting a new data file)
 * trialStop: stop recording
 * experimentStop: disconnect from Intan
 */
public class IntanRecordingController implements TrialEventListener, ExperimentEventListener {

    @Dependency
    protected boolean recordingEnabled;

    @Dependency
    protected IntanFileNamingStrategy<Long> fileNamingStrategy;

    @Dependency
    private IntanRHD intan;

    protected boolean connected = false;

    @Override
    public void experimentStart(long timestamp) {
        tryConnection();
        if (toRecord()) {
            fileNamingStrategy.rename(timestamp);
            getIntan().record();
        }
    }

    @Override
    public void trialInit(long timestamp, TrialContext context) {
        if (recordingEnabled && !connected)
            tryConnection();
        if (toRecord()) {
            fileNamingStrategy.rename(timestamp);
            getIntan().record();
        }
    }

    @Override
    public void trialStop(long timestamp, TrialContext context) {

    }

    @Override
    public void experimentStop(long timestamp) {
        if (toRecord())
            getIntan().stopRecording();

        if (toRecord()) {
            getIntan().stop();
            getIntan().disconnect();
        }

        connected = false;
    }

    private void tryConnection() {
        try {
            getIntan().connect();
            connected = true;
        } catch (RemoteException e) {
            System.err.println("Could not connect to Intan, disabling Intan functionality");
            connected = false;
        }
    }

    protected boolean toRecord() {
        return connected && recordingEnabled;
    }

    @Override
    public void trialStart(long timestamp, TrialContext context) {
        if (toRecord()){
            String note = Long.toString(context.getCurrentTask().getTaskId());
            getIntan().writeNote(note);
        }
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

    public boolean isRecordingEnabled() {
        return recordingEnabled;
    }

    public void setRecordingEnabled(boolean recordingEnabled) {
        this.recordingEnabled = recordingEnabled;
    }

    public IntanRHD getIntan() {
        return intan;
    }

    public void setIntan(IntanRHD intanRHD) {
        this.intan = intanRHD;
    }

    public IntanFileNamingStrategy<Long> getFileNamingStrategy() {
        return fileNamingStrategy;
    }

    public void setFileNamingStrategy(IntanFileNamingStrategy<Long> fileNamingStrategy) {
        this.fileNamingStrategy = fileNamingStrategy;
    }
}