package org.xper.allen.nafc.console;

import com.thoughtworks.xstream.XStream;

/**
 * This is a value object class. Its job is to hold the TrialStatistics and fetch/modify them when necessary. 
 * @author Allen Chen
 *
 */
public class NAFCTrialStatistics{
	// These two are actually kind of useless, since there are existing fields that can used in TrialStatistics. However I kept this in here as a model in case i need to add something novel in the future
	// 
	
	int fixationSuccess = 0;
	int fixationEyeInFail = 0;
	int fixationEyeInHoldFail = 0;
	
	int sampleSuccess = 0;
	int sampleEyeInHoldFail = 0;
	
	int choiceCorrect = 0;
	int choiceIncorrect = 0;
	int choiceRewardedIncorrect = 0;
	int choiceEyeFail = 0;
	
	int completeTrials = 0;


	public void reset() {

		fixationSuccess = 0;
		fixationEyeInFail = 0;
		fixationEyeInHoldFail = 0;
		
		sampleSuccess = 0;
		sampleEyeInHoldFail = 0;
		
		choiceCorrect = 0;
		choiceIncorrect = 0;
		choiceRewardedIncorrect = 0;
		choiceEyeFail = 0;
		
		completeTrials = 0;
	}

	static XStream xstream = new XStream();
	
	static {
		xstream.alias("TrialStatistics", NAFCTrialStatistics.class);
	}
	
	public static NAFCTrialStatistics fromXml (String xml) {
		return (NAFCTrialStatistics)xstream.fromXML(xml);
	}
	
	public static String toXml (NAFCTrialStatistics msg) {
		return xstream.toXML(msg);
	}

	public int getFixationSuccess() {
		return fixationSuccess;
	}

	public void setFixationSuccess(int fixationSuccess) {
		this.fixationSuccess = fixationSuccess;
	}

	public int getFixationEyeInFail() {
		return fixationEyeInFail;
	}

	public void setFixationEyeInFail(int fixationEyeInFail) {
		this.fixationEyeInFail = fixationEyeInFail;
	}

	public int getFixationEyeInHoldFail() {
		return fixationEyeInHoldFail;
	}

	public void setFixationEyeInHoldFail(int fixationEyeInHoldFail) {
		this.fixationEyeInHoldFail = fixationEyeInHoldFail;
	}

	public int getSampleSuccess() {
		return sampleSuccess;
	}

	public void setSampleSuccess(int sampleSuccess) {
		this.sampleSuccess = sampleSuccess;
	}

	public int getSampleEyeInHoldFail() {
		return sampleEyeInHoldFail;
	}

	public void setSampleEyeInHoldFail(int sampleEyeInHoldFail) {
		this.sampleEyeInHoldFail = sampleEyeInHoldFail;
	}

	public int getChoiceCorrect() {
		return choiceCorrect;
	}

	public void setChoiceCorrect(int choiceCorrect) {
		this.choiceCorrect = choiceCorrect;
	}

	public int getChoiceIncorrect() {
		return choiceIncorrect;
	}

	public void setChoiceIncorrect(int choiceIncorrect) {
		this.choiceIncorrect = choiceIncorrect;
	}

	public int getChoiceEyeFail() {
		return choiceEyeFail;
	}

	public void setChoiceEyeFail(int choiceEyeFail) {
		this.choiceEyeFail = choiceEyeFail;
	}

	public int getChoiceRewardedIncorrect() {
		return choiceRewardedIncorrect;
	}

	public void setChoiceRewardedIncorrect(int choiceRewardedIncorrect) {
		this.choiceRewardedIncorrect = choiceRewardedIncorrect;
	}

	public int getCompleteTrials() {
		return completeTrials;
	}

	public void setCompleteTrials(int completeTrials) {
		this.completeTrials = completeTrials;
	}

	
	

}
