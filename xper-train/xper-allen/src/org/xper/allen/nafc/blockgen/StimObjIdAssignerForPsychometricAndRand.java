package org.xper.allen.nafc.blockgen;

import java.util.LinkedList;
import java.util.List;

import org.xper.time.TimeUtil;

public class StimObjIdAssignerForPsychometricAndRand implements StimObjIdAssigner {
	private static TimeUtil globalTimeUtil;
	private NumberOfDistractors numDistractors;
	
	private StimObjIdsForMixedPsychometricAndRand stimObjIds = new StimObjIdsForMixedPsychometricAndRand(new LinkedList<Long>(),
			new LinkedList<Long>(), new LinkedList<Long>());


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
		stimObjIds.sampleId = globalTimeUtil.currentTimeMicros();
		stimObjIds.matchId = stimObjIds.sampleId+1;
		long prevId = stimObjIds.matchId;
		for (int j=0; j<numDistractors.numPsychometricDistractors;j++) {
			stimObjIds.allDistractorsIds.add(prevId+1);
			stimObjIds.psychometricDistractorsIds.add(prevId+1);
			prevId++;
		}
		for (int j=0; j<numDistractors.numRandDistractors;j++) {
			stimObjIds.allDistractorsIds.add(prevId+1);
			stimObjIds.randDistractorsIds.add(prevId+1);
			prevId++;
		}
		
	}

	public Long getSampleId() {
		return stimObjIds.sampleId;
	}

	public void setSampleId(Long sampleId) {
		this.stimObjIds.sampleId = sampleId;
	}

	public Long getMatchId() {
		return stimObjIds.matchId;
	}

	public List<Long> getAllDistractorsIds() {
		return stimObjIds.allDistractorsIds;
	}

	public List<Long> getPsychometricDistractorsIds() {
		return stimObjIds.psychometricDistractorsIds;
	}

	public List<Long> getRandDistractorsIds() {
		return stimObjIds.randDistractorsIds;
	}
	
	
}