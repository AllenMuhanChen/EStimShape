package org.xper.sach.util;

import java.util.List;

import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialResult;
import org.xper.sach.SachTrialEventListener;
import org.xper.sach.vo.SachTrialContext;

public class SachEventUtil {

	public static void fireTargetOnEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners,	SachTrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			if (listener instanceof SachTrialEventListener) {
				((SachTrialEventListener)listener).targetOn(timestamp, currentContext);
			}
		}
	}

	/*public static void fireTargetInitialSelectionEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners, SachTrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			if (listener instanceof SachTrialEventListener) {
				((SachTrialEventListener)listener).targetInitialSelection(timestamp, currentContext);
			}
		}
	}*/
	
	public static void fireTargetSelectionSuccessEvent(long timestamp, List<? extends TrialEventListener> trialEventListeners, SachTrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			if (listener instanceof SachTrialEventListener) {
				((SachTrialEventListener)listener).targetSelectionSuccess(timestamp, currentContext);
			}
		}
	}
	
	// added by shs for behavioral tracking:
	public static void fireTrialPASSEvent(long timestamp, List<? extends TrialEventListener> trialEventListeners, SachTrialContext currentContext) {
		System.out.println("--PASS (non-target trial)--");

		for (TrialEventListener listener : trialEventListeners) {
			if (listener instanceof SachTrialEventListener) {
				((SachTrialEventListener)listener).trialPASS(timestamp, currentContext);
			}
		}
	}
	
	public static void fireTrialTARGETPASSEvent(long timestamp, List<? extends TrialEventListener> trialEventListeners, SachTrialContext currentContext,long requiredTargetSelectionHoldTime, long targetOnLocalTime) {
		System.out.println("--PASS (Target selection time= " + ((timestamp - targetOnLocalTime)/1000 - requiredTargetSelectionHoldTime) + ")--");

		for (TrialEventListener listener : trialEventListeners) {
			if (listener instanceof SachTrialEventListener) {
				((SachTrialEventListener)listener).trialPASS(timestamp, currentContext);
			}
		}
	}
	
	public static void fireTrialTARGETFAILEvent(long timestamp, List<? extends TrialEventListener> trialEventListeners, 
			SachTrialContext currentContext, TrialResult targetResult, long targetOnLocalTime) {

		if (targetResult == TrialResult.TARGET_SELECTION_EYE_FAIL) {
			System.out.println("--FAIL (Target timeout time= " + (timestamp - targetOnLocalTime)/1000 + ")--");
		} else if (targetResult == TrialResult.TARGET_SELECTION_EYE_BREAK) {
			System.out.println("--FAIL (Target break time= " + (timestamp - targetOnLocalTime)/1000 + ")--");
		} else {
			System.out.println("--FAIL (Target, unknown error)");
		}
		
		for (TrialEventListener listener : trialEventListeners) {
			if (listener instanceof SachTrialEventListener) {
				((SachTrialEventListener)listener).trialFAIL(timestamp, currentContext);
			}
		}
	}
	
	public static void fireTrialFAILEvent(long timestamp, List<? extends TrialEventListener> trialEventListeners, SachTrialContext currentContext) {
		System.out.println("--FAIL (non-target trial)--");
		for (TrialEventListener listener : trialEventListeners) {
			if (listener instanceof SachTrialEventListener) {
				((SachTrialEventListener)listener).trialFAIL(timestamp, currentContext);
			}
		}
	}
	
	public static void fireTrialBREAKEvent(long timestamp, List<? extends TrialEventListener> trialEventListeners, SachTrialContext currentContext,int slideNum, boolean isISI) {
		if (isISI) {
			System.out.println("--BREAK (ISI #" + slideNum + ")--");
		} else {
			System.out.println("--BREAK (slide #" + slideNum + ")--");
		}
		for (TrialEventListener listener : trialEventListeners) {
			if (listener instanceof SachTrialEventListener) {
				((SachTrialEventListener)listener).trialBREAK(timestamp, currentContext);
			}
		}
	}
	
	public static void fireTrialNOGOEvent(long timestamp,
			List<? extends TrialEventListener> trialEventListeners, SachTrialContext currentContext) {
		for (TrialEventListener listener : trialEventListeners) {
			if (listener instanceof SachTrialEventListener) {
				((SachTrialEventListener)listener).trialNOGO(timestamp, currentContext);
			}
		}
	}
}
