package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.NumberOfDistractorsForPsychometricTrial;
import org.xper.time.TimeUtil;

public class StimObjIdAssignerForPsychometricTrials{
	private static TimeUtil globalTimeUtil;
	private NumberOfDistractorsForPsychometricTrial numDistractors;
	


	public StimObjIdAssignerForPsychometricTrials(TimeUtil globalTimeUtil, NumberOfDistractorsForPsychometricTrial numDistractors) {
		StimObjIdAssignerForPsychometricTrials.globalTimeUtil = globalTimeUtil;
		this.numDistractors = numDistractors;
	}
	
	private Psychometric<Long> stimObjIds = new Psychometric<Long>();


	public void assignStimObjIds() {
		stimObjIds.setSample(globalTimeUtil.currentTimeMicros());
		stimObjIds.setMatch(stimObjIds.getSample()+1);
		long prevId = stimObjIds.getMatch();
		for (int j = 0; j< numDistractors.getNumPsychometricDistractors(); j++) {
			stimObjIds.addPsychometricDistractor(prevId+1);
			prevId++;
		}
		for (int j = 0; j< numDistractors.getNumRandDistractors(); j++) {
			stimObjIds.addRandDistractor(prevId+1);
			prevId++;
		}
		
	}

	public Psychometric<Long> getStimObjIds() {
		return stimObjIds;
	}
}