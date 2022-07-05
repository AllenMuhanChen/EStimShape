package org.xper.allen.nafc.blockgen;

import java.util.LinkedList;
import java.util.List;

import org.xper.time.TimeUtil;

public class StimObjIdAssignerForPsychometricAndRand implements StimObjIdAssigner {
	private static TimeUtil globalTimeUtil;
	private NumberOfDistractors numDistractors;
	
	private Long sampleId;
	private Long matchId;
	private List<Long> allDistractorsIds = new LinkedList<Long>();
	private List<Long> psychometricDistractorsIds = new LinkedList<Long>();
	private List<Long> randDistractorsIds = new LinkedList<Long>();
	
	
	public StimObjIdAssignerForPsychometricAndRand(TimeUtil globalTimeUtil, NumberOfDistractors numDistractors) {
		StimObjIdAssignerForPsychometricAndRand.globalTimeUtil = globalTimeUtil;
		this.numDistractors = numDistractors;
	}
	
	/**
	 * assigns sample, match and distractor Ids that will be written to the DB. sampleId is required
	 * for generating noisemaps!
	 * @param psychometricNoisyMStickPngTrial TODO
	 */
	public void assignStimObjIds() {
		sampleId = globalTimeUtil.currentTimeMicros();
		matchId = sampleId+1;
		long prevId = matchId;
		for (int j=0; j<numDistractors.numPsychometricDistractors;j++) {
			allDistractorsIds.add(prevId+1);
			psychometricDistractorsIds.add(prevId+1);
			prevId++;
		}
		for (int j=0; j<numDistractors.numRandDistractors;j++) {
			allDistractorsIds.add(prevId+1);
			randDistractorsIds.add(prevId+1);
			prevId++;
		}
		
	}

	public Long getSampleId() {
		return sampleId;
	}

	public void setSampleId(Long sampleId) {
		this.sampleId = sampleId;
	}

	public Long getMatchId() {
		return matchId;
	}

	public List<Long> getAllDistractorsIds() {
		return allDistractorsIds;
	}

	public List<Long> getPsychometricDistractorsIds() {
		return psychometricDistractorsIds;
	}

	public List<Long> getRandDistractorsIds() {
		return randDistractorsIds;
	}
	
	
}