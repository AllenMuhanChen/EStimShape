package org.xper.classic.vo;

/**
 * TrialResult is NOT used to log trial events either to database or the console screen.
 * It's used internally in the Experiment Object and related SlideRunner an TrialRunner objects.
 * @author john
 *
 */
public enum TrialResult {
	INITIAL_EYE_IN_FAIL, EYE_IN_HOLD_FAIL, FIXATION_SUCCESS, 
	SLIDE_OK, TRIAL_COMPLETE, EYE_BREAK, 
	NO_MORE_TASKS, EXPERIMENT_STOPPING,
	TARGET_SELECTION_EYE_FAIL, TARGET_SELECTION_EYE_BREAK, TARGET_SELECTION_DONE
}
