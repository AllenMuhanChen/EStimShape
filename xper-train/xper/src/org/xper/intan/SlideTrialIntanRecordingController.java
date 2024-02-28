package org.xper.intan;

import org.xper.Dependency;
import org.xper.classic.SlideEventListener;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.exception.RemoteException;
import org.xper.experiment.listener.ExperimentEventListener;

/**
 * slideOn: write a liveNote to Intan to tell what the taskId is
 */
public class SlideTrialIntanRecordingController extends IntanRecordingController implements SlideEventListener {

    /**
     * Live notes cannot be more accurate than 300 ms due to the communication delay of USB
     * @param index
     * @param timestamp
     * @param taskId
     */
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

    @Override
    public void trialStart(long timestamp, TrialContext context) {
        //Do nothing instead of writing livenote of taskId.
    }

}