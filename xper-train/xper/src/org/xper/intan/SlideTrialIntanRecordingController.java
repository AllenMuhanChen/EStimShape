package org.xper.intan;

import org.xper.Dependency;
import org.xper.classic.SlideEventListener;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.exception.RemoteException;
import org.xper.experiment.listener.ExperimentEventListener;


public class SlideTrialIntanRecordingController extends IntanRecordingController implements SlideEventListener {

    @Override
    public void slideOn(int index, long timestamp, long taskId) {
        if (toRecord()){
            String note = Long.toString(taskId);
            getIntan().writeNote(note);
        }
    }

    @Override
    public void slideOff(int index, long timestamp, int frameCount, long taskId) {

    }

}