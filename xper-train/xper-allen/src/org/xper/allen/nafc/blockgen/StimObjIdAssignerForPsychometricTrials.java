package org.xper.allen.nafc.blockgen;

import java.util.LinkedList;
import java.util.List;

import org.xper.time.TimeUtil;

public class StimObjIdAssignerForPsychometricTrials{
	private static TimeUtil globalTimeUtil;
	private NumberOfDistractors numDistractors;
	


	public StimObjIdAssignerForPsychometricTrials(TimeUtil globalTimeUtil, NumberOfDistractors numDistractors) {
		StimObjIdAssignerForPsychometricTrials.globalTimeUtil = globalTimeUtil;
		this.numDistractors = numDistractors;
	}
	
	private StimObjIdsForMixedPsychometricAndRand stimObjIds = new StimObjIdsForMixedPsychometricAndRand(new LinkedList<Long>(),
			new LinkedList<Long>(), new LinkedList<Long>());

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

	public StimObjIdsForMixedPsychometricAndRand getStimObjIds() {
		return stimObjIds;
	}
}