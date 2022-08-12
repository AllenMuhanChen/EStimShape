package org.xper.eye;

import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import org.xper.classic.vo.TrialResult;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.ThreadException;
import org.xper.time.TimeUtil;

public class EyeTargetSelectorConcurrentDriver {
	
	EyeTargetSelector selector;
	TimeUtil timeUtil;
	
	ExecutorService exec;
	Future<TargetSelectorResult> task;
	
	public EyeTargetSelectorConcurrentDriver (EyeTargetSelector selector, TimeUtil timeUtil) {
		this.selector = selector;
		this.timeUtil = timeUtil;
	}
	
	/*
	 * This is running in a separate thread that is different from the main experiment thread where the Experiment objects run.
	 * Note: both the deadlineIntialEyeIn and eyeHoldTime are in micro seconds.
	 */
	public void start(final Coordinates2D targetCenter [], final double targetWinSize[], 
			final long deadlineIntialEyeIn, final long eyeHoldTime) {
		exec = Executors.newSingleThreadExecutor();
		
		task = exec.submit(new Callable<TargetSelectorResult>() {
			public TargetSelectorResult call() throws Exception {
				TargetSelectorResult result = new TargetSelectorResult();
				
				int sel = selector.waitInitialSelection(targetCenter, targetWinSize, deadlineIntialEyeIn);
				if (sel < 0) {
					result.setSelectionStatusResult(TrialResult.TARGET_SELECTION_EYE_FAIL);
					return result;
				}
				
				long initialEyeInTime = timeUtil.currentTimeMicros();
				result.setTargetInitialSelectionLocalTime(initialEyeInTime);
				
				boolean success = selector.waitEyeHold(sel, initialEyeInTime + eyeHoldTime);
				if (!success) {
					result.setSelectionStatusResult(TrialResult.TARGET_SELECTION_EYE_BREAK);
					return result;
				}
				
				result.setSelection(sel);
				result.setSelectionStatusResult(TrialResult.TARGET_SELECTION_DONE);
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
	
	public TargetSelectorResult getResult() {
		try {
			return task.get();
		} catch (Exception e) {
			throw new ThreadException(e);
		}
	}
}
