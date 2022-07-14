package org.xper.allen.nafc.blockgen.psychometric;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.nafc.blockgen.NumberOfDistractors;
import org.xper.allen.nafc.blockgen.StimObjIdsForMixedPsychometricAndRand;
import org.xper.time.TimeUtil;

public class StimObjIdAssignerForPsychometricTrials{
	private static TimeUtil globalTimeUtil;
	private NumberOfDistractors numDistractors;
	


	public StimObjIdAssignerForPsychometricTrials(TimeUtil globalTimeUtil, NumberOfDistractors numDistractors) {
		StimObjIdAssignerForPsychometricTrials.globalTimeUtil = globalTimeUtil;
		this.numDistractors = numDistractors;
	}
	
	private Psychometric<Long> stimObjIds = new Psychometric<Long>();

	/**
	 * assigns sample, match and distractor Ids that will be written to the DB. sampleId is required
	 * for generating noisemaps!
	 * @param psychometricNoisyMStickPngTrial TODO
	 */
	public void assignStimObjIds() {
		stimObjIds.setSample(globalTimeUtil.currentTimeMicros());
		stimObjIds.setMatch(stimObjIds.getSample()+1);
		long prevId = stimObjIds.getMatch();
		for (int j=0; j<numDistractors.numPsychometricDistractors;j++) {
			stimObjIds.addPsychometricDistractor(prevId+1);
			prevId++;
		}
		for (int j=0; j<numDistractors.numRandDistractors;j++) {
			stimObjIds.addRandDistractor(prevId+1);
			prevId++;
		}
		
	}

	public Psychometric<Long> getStimObjIds() {
		return stimObjIds;
	}
}