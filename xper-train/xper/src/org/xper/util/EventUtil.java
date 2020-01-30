package org.xper.util;

import java.util.List;

import org.xper.classic.SlideEventListener;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.drawing.Coordinates2D;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.fixcal.FixCalEventListener;

public class EventUtil {

	public static void fireInitialEyeInSucceedEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners,
			TrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			listener.initialEyeInSucceed(timestamp, currentContext);
		}
	}

	public static void fireTrialStopEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners,
			TrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			listener.trialStop(timestamp, currentContext);
		}
	}
	
	public static void fireTrialInitEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners,
			TrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			listener.trialInit(timestamp, currentContext);
		}
	}

	public static void fireTrialStartEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners,
			TrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			listener.trialStart(timestamp, currentContext);
		}
	}

	public static void fireFixationPointOnEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners,
			TrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			listener.fixationPointOn(timestamp, currentContext);
		}
	}

	public static void fireInitialEyeInFailEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners,
			TrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			listener.initialEyeInFail(timestamp, currentContext);
		}
	}

	public static void fireEyeInHoldFailEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners,
			TrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			listener.eyeInHoldFail(timestamp, currentContext);
		}
	}

	public static void fireFixationSucceedEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners,
			TrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			listener.fixationSucceed(timestamp, currentContext);
		}
	}

	public static void fireEyeInBreakEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners,
			TrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			listener.eyeInBreak(timestamp, currentContext);
		}
	}

	public static void fireTrialCompleteEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners,
			TrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			listener.trialComplete(timestamp, currentContext);
		}
	}

	public static void fireSlideOnEvent(int index, long timestamp,
			List<? extends SlideEventListener> slideEventListeners) {
		for (SlideEventListener listener : slideEventListeners) {
			listener.slideOn(index, timestamp);
		}
	}

	public static void fireSlideOffEvent(int index, long timestamp,
			int frameCount,
			List<? extends SlideEventListener> slideEventListeners) {
		for (SlideEventListener listener : slideEventListeners) {
			listener.slideOff(index, timestamp, frameCount);
		}
	}

	public static void fireExperimentStartEvent(long timestamp,
			List<? extends ExperimentEventListener> experimentEventListeners) {
		for (ExperimentEventListener listener : experimentEventListeners) {
			listener.experimentStart(timestamp);
		}
	}

	public static void fireExperimentStopEvent(long timestamp,
			List<? extends ExperimentEventListener> experimentEventListeners) {
		for (ExperimentEventListener listener : experimentEventListeners) {
			listener.experimentStop(timestamp);
		}
	}
	
	public static void fireCalibrationPointSetupEvent (long timestamp, 
			List<? extends TrialEventListener> eventListeners, 
			Coordinates2D pos, TrialContext context) {
		for (TrialEventListener listener : eventListeners) {
			if (listener instanceof FixCalEventListener) {
				((FixCalEventListener)listener).calibrationPointSetup(timestamp, pos, context);
			}
		}
	}
}
