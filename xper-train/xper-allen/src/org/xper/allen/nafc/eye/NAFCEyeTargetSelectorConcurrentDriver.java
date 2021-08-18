package org.xper.allen.nafc.eye;

import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import org.xper.allen.nafc.vo.NAFCTrialResult;
import org.xper.classic.vo.TrialResult;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.ThreadException;
import org.xper.eye.EyeTargetSelector;
import org.xper.eye.TargetSelectorResult;
import org.xper.time.TimeUtil;

public class NAFCEyeTargetSelectorConcurrentDriver {
	
	EyeTargetSelector selector;
	TimeUtil timeUtil;
	
	ExecutorService exec;
	Future<NAFCTargetSelectorResult> task;
	
	public NAFCEyeTargetSelectorConcurrentDriver (EyeTargetSelector selector, TimeUtil timeUtil) {
		this.selector = selector;
		this.timeUtil = timeUtil;
	}
	
	/*
	 * This is running in a separate thread that is different from the main experiment thread where the Experiment objects run.
	 * Note: both the deadlineIntialEyeIn and eyeHoldTime are in micro seconds.
	 */
	public void start(final Coordinates2D[] targetCenter, final double[] targetWinSize, 
			final long deadlineIntialEyeIn, final long eyeHoldTime) {
		

		exec = Executors.newSingleThreadExecutor();
		
		task = exec.submit(new Callable<NAFCTargetSelectorResult>() {
			public NAFCTargetSelectorResult call() throws Exception {
				NAFCTargetSelectorResult result = new NAFCTargetSelectorResult();
				int sel = selector.waitInitialSelection(targetCenter, targetWinSize, deadlineIntialEyeIn);
				System.out.println("sel = " + sel);
				if (sel < 0) {
					result.setSelectionStatusResult(NAFCTrialResult.TARGET_SELECTION_EYE_FAIL);
					return result;
				}
				
				long initialEyeInTime = timeUtil.currentTimeMicros();
				result.setTargetInitialSelectionLocalTime(initialEyeInTime);
				
				boolean success = selector.waitEyeHold(sel, initialEyeInTime + eyeHoldTime);
				/* Commented out b/c we don't want an eye break to stop the trial
				if (!success) {
					result.setSelectionStatusResult(NAFCTrialResult.TARGET_SELECTION_EYE_BREAK);
					return result;
				}
				*/
				result.setSelection(sel);
				/* Old selection method for 2AFC
				if (sel == 0 ) {
				result.setSelectionStatusResult(NAFCTrialResult.TARGET_SELECTION_ONE);
				}
				else if(sel==1) {
				result.setSelectionStatusResult(NAFCTrialResult.TARGET_SELECTION_TWO);
				}
				*/
				
				if (sel > -1) {
					result.setSelectionStatusResult(NAFCTrialResult.TARGET_SELECTION_SUCCESS);
				}
				return result;
			}
		});
	}
	
	public void stop () {
		exec.shutdown();
	}
	
	public boolean isDone () {
		return task.isDone();
	}
	
	public NAFCTargetSelectorResult getResult() {
		try {
			return task.get();
		} catch (Exception e) {
			throw new ThreadException(e);
		}
	}
}
