package org.xper.allen.twoac.eye;

import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import org.xper.allen.vo.TwoACTrialResult;
import org.xper.classic.vo.TrialResult;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.ThreadException;
import org.xper.eye.EyeTargetSelector;
import org.xper.eye.TargetSelectorResult;
import org.xper.time.TimeUtil;

public class TwoACEyeTargetSelectorConcurrentDriver {
	
	EyeTargetSelector selector;
	TimeUtil timeUtil;
	
	ExecutorService exec;
	Future<TwoACTargetSelectorResult> task;
	
	public TwoACEyeTargetSelectorConcurrentDriver (EyeTargetSelector selector, TimeUtil timeUtil) {
		this.selector = selector;
		this.timeUtil = timeUtil;
	}
	
	/*
	 * This is running in a separate thread that is different from the main experiment thread where the Experiment objects run.
	 * Note: both the deadlineIntialEyeIn and eyeHoldTime are in micro seconds.
	 */
	public void start(final Coordinates2D targetCenter[], final double targetWinSize[], 
			final long deadlineIntialEyeIn, final long eyeHoldTime) {
		exec = Executors.newSingleThreadExecutor();
		
		task = exec.submit(new Callable<TwoACTargetSelectorResult>() {
			public TwoACTargetSelectorResult call() throws Exception {
				TwoACTargetSelectorResult result = new TwoACTargetSelectorResult();
				int sel = selector.waitInitialSelection(targetCenter, targetWinSize, deadlineIntialEyeIn);
				System.out.println("sel = " + sel);
				if (sel < 0) {
					result.setSelectionStatusResult(TwoACTrialResult.TARGET_SELECTION_EYE_FAIL);
					return result;
				}
				
				long initialEyeInTime = timeUtil.currentTimeMicros();
				result.setTargetInitialSelectionLocalTime(initialEyeInTime);
				
				boolean success = selector.waitEyeHold(sel, initialEyeInTime + eyeHoldTime);
				if (!success) {
					result.setSelectionStatusResult(TwoACTrialResult.TARGET_SELECTION_EYE_BREAK);
					return result;
				}
				
				result.setSelection(sel);
				if (sel == 0 ) {
				result.setSelectionStatusResult(TwoACTrialResult.TARGET_SELECTION_ONE);
				}
				else if(sel==1) {
				result.setSelectionStatusResult(TwoACTrialResult.TARGET_SELECTION_TWO);
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
	
	public TwoACTargetSelectorResult getResult() {
		try {
			return task.get();
		} catch (Exception e) {
			throw new ThreadException(e);
		}
	}
}
