package org.xper.intan;

import org.xper.Dependency;
import org.xper.classic.SlideEventListener;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.exception.RemoteException;
import org.xper.experiment.listener.ExperimentEventListener;

/**
 * Controls what trial events and experiment events trigger what events in IntanController.
 */
public class IntanRecordingSlideMessageDispatcher implements SlideEventListener, ExperimentEventListener{

    @Dependency
    private
    IntanRecordingController intanController;

    @Dependency
    IntanFileNamingStrategy<Long> fileNamingStrategy;

    private boolean connected = false;

    @Override
    public void slideOn(int index, long timestamp, long taskId) {
        if (connected) {
            fileNamingStrategy.rename(taskId);
            getIntanController().record();
        }
    }

    @Override
    public void slideOff(int index, long timestamp, int frameCount, long taskId) {
        if (connected)
            getIntanController().stopRecording();
    }

    @Override
    public void experimentStart(long timestamp) {
        tryConnection();
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
    public void experimentStop(long timestamp) {
        if (connected) {
            getIntanController().stop();
            getIntanController().disconnect();
        }
        connected = false;
    }


    public IntanRecordingController getIntanController() {
        return intanController;
    }

    public void setIntanController(IntanRecordingController intanRecordingController) {
        this.intanController = intanRecordingController;
    }

    public IntanFileNamingStrategy getFileNamingStrategy() {
        return fileNamingStrategy;
    }

    public void setFileNamingStrategy(IntanFileNamingStrategy fileNamingStrategy) {
        this.fileNamingStrategy = fileNamingStrategy;
    }


}