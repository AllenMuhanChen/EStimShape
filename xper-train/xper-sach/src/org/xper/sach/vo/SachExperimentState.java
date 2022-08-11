package org.xper.sach.vo;

import org.dom4j.Document;
import org.xper.Dependency;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.eye.EyeTargetSelector;

/**
 * Target position and size describe the response window.
 * 
 * @author john
 *
 */
public class SachExperimentState extends SlideTrialExperimentState {
	@Dependency
	EyeTargetSelector targetSelector;
	
	/**
	 * in ms
	 */
	@Dependency
	long timeAllowedForInitialTargetSelection;
	@Dependency
	long requiredTargetSelectionHoldTime;
	@Dependency
	long targetSelectionStartDelay;
	@Dependency
	long timeoutPenaltyDelay = 0;	// -shs, default to zero
	@Dependency
	long correctStreak = 0;	// -shs, default to zero
	@Dependency
	boolean repeatTrialIfEyeBreak = false;
	@Dependency
	double minJuice = 200;	// -shs, default to zero
	@Dependency
	long timeoutBaseDelay = 1500;	// -shs, default to zero

	Document currentSpecDoc;
	
	public SachExperimentState () {
	}

	public Document getCurrentSpecDoc() {
		return currentSpecDoc;
	}

	public void setCurrentSpecDoc(Document currentSpecDoc) {
		this.currentSpecDoc = currentSpecDoc;
	}

	public EyeTargetSelector getTargetSelector() {
		return targetSelector;
	}

	public void setTargetSelector(EyeTargetSelector targetSelector) {
		this.targetSelector = targetSelector;
	}

	public long getTimeAllowedForInitialTargetSelection() {
		return timeAllowedForInitialTargetSelection;
	}

	public void setTimeAllowedForInitialTargetSelection(
			long timeAllowedForInitialTargetSelection) {
		this.timeAllowedForInitialTargetSelection = timeAllowedForInitialTargetSelection;
	}

	public long getRequiredTargetSelectionHoldTime() {
		return requiredTargetSelectionHoldTime;
	}

	public void setRequiredTargetSelectionHoldTime(
			long requiredTargetSelectionHoldTime) {
		this.requiredTargetSelectionHoldTime = requiredTargetSelectionHoldTime;
	}

	public long getTargetSelectionStartDelay() {
		return targetSelectionStartDelay;
	}

	public void setTargetSelectionStartDelay(long targetSelectionStartDelay) {
		this.targetSelectionStartDelay = targetSelectionStartDelay;
	}

	public long getTimeoutPenaltyDelay() { // -shs
		return timeoutPenaltyDelay;
	}
	
	public void setTimeoutPenaltyDelay(long timeoutPenaltyDelay) {	// -shs
		this.timeoutPenaltyDelay = timeoutPenaltyDelay;
	}
	
	public void incrementStreak() { // -ram
		correctStreak++;
	}
	
	public void resetStreak() {	// -ram
		correctStreak = 0;
	}
	
	public long getStreak() { // -ram
		return correctStreak;
	}
	
	public boolean isRepeatTrialIfEyeBreak() {
		return repeatTrialIfEyeBreak;
	}

	public void setRepeatTrialIfEyeBreak(boolean repeatTrialIfEyeBreak) {
		this.repeatTrialIfEyeBreak = repeatTrialIfEyeBreak;
	}
	
	public void setMinJuice(double minJuice) {
		this.minJuice = minJuice;
	}
	
	public double getMinJuice() {
		return minJuice;
	}
	
	public void setTimeoutBaseDelay(long timeoutBaseDelay) {
		this.timeoutBaseDelay = timeoutBaseDelay;
	}
	
	public long getTimeoutBaseDelay() {
		return timeoutBaseDelay;
	}
}
