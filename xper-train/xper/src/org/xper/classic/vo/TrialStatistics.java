package org.xper.classic.vo;

import com.thoughtworks.xstream.XStream;

public class TrialStatistics {
	protected int completeTrials = 0;
	protected int failedTrials = 0;
	protected int brokenTrials = 0;
	
	protected int allTrialsPASS = 0;
	protected int allTrialsFAIL = 0;
	protected int allTrialsBREAK = 0;
	protected int allTrialsNOGO = 0;
	
	public void reset() {
		completeTrials = 0;
		failedTrials = 0;
		brokenTrials = 0;
		
		allTrialsPASS = 0;
		allTrialsFAIL = 0;
		allTrialsBREAK = 0;
		allTrialsNOGO = 0;
	}
	
	static XStream xstream = new XStream();

	static {
		xstream.alias("TrialStatistics", TrialStatistics.class);
	}
	
	public static TrialStatistics fromXml (String xml) {
		return (TrialStatistics)xstream.fromXML(xml);
	}
	
	public static String toXml (TrialStatistics msg) {
		return xstream.toXML(msg);
	}

	public int getCompleteTrials() {
		return completeTrials;
	}

	public void setCompleteTrials(int completeTrials) {
		this.completeTrials = completeTrials;
	}

	public int getFailedTrials() {
		return failedTrials;
	}

	public void setFailedTrials(int failedTrials) {
		this.failedTrials = failedTrials;
	}

	public int getBrokenTrials() {
		return brokenTrials;
	}

	public void setBrokenTrials(int brokenTrials) {
		this.brokenTrials = brokenTrials;
	}

	public int getAllTrialsPASS() {
		return allTrialsPASS;
	}

	public void setAllTrialsPASS(int allTrialsPASS) {
		this.allTrialsPASS = allTrialsPASS;
	}

	public int getAllTrialsFAIL() {
		return allTrialsFAIL;
	}

	public void setAllTrialsFAIL(int allTrialsFAIL) {
		this.allTrialsFAIL = allTrialsFAIL;
	}

	public int getAllTrialsBREAK() {
		return allTrialsBREAK;
	}

	public void setAllTrialsBREAK(int allTrialsBREAK) {
		this.allTrialsBREAK = allTrialsBREAK;
	}
	
	public int getAllTrialsNOGO() {
		return allTrialsNOGO;
	}

	public void setAllTrialsNOGO(int allTrialsNOGO) {
		this.allTrialsNOGO = allTrialsNOGO;
	}
}
