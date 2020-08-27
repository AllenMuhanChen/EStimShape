package org.xper.allen.db.vo;

import org.xper.classic.vo.TrialStatistics;

import com.thoughtworks.xstream.XStream;

/**
 * This is a value object class. Its job is to hold the TrialStatistics and fetch/modify them when necessary. 
 * @author Allen Chen
 *
 */
public class SaccadeTrialStatistics extends TrialStatistics{
	// These two are actually kind of useless, since there are existing fields that can used in TrialStatistics. However I kept this in here as a model in case i need to add something novel in the future
	// 
	int targetSelectionEyeFail = 0;
	int targetSelectionEyeBreak = 0;
	


	
	public void reset() {
		completeTrials = 0;
		failedTrials = 0;
		brokenTrials = 0;
		
		allTrialsPASS = 0;
		allTrialsFAIL = 0;
		allTrialsBREAK = 0;
		allTrialsNOGO = 0;
		
		targetSelectionEyeFail = 0;
		targetSelectionEyeBreak = 0;
	}

	static XStream xstream = new XStream();
	
	static {
		xstream.alias("TrialStatistics", SaccadeTrialStatistics.class);
	}
	
	public static SaccadeTrialStatistics fromXml (String xml) {
		return (SaccadeTrialStatistics)xstream.fromXML(xml);
	}
	
	public static String toXml (SaccadeTrialStatistics msg) {
		return xstream.toXML(msg);
	}
	
	public int getTargetSelectionEyeFail() {
		return targetSelectionEyeFail;
	}

	public void setTargetSelectionEyeFail(int targetSelectionEyeFail) {
		this.targetSelectionEyeFail = targetSelectionEyeFail;
	}

	public int getTargetSelectionEyeBreak() {
		return targetSelectionEyeBreak;
	}

	public void setTargetSelectionEyeBreak(int targetSelectionEyeBreak) {
		this.targetSelectionEyeBreak = targetSelectionEyeBreak;
	}
	

}
