package org.xper.allen.nafc.blockgen.rand;

import org.xper.time.TimeUtil;

public class StimObjIdAssignerForRandTrials{
	private TimeUtil globalTimeUtil;
	private NumberOfDistractorsForRandTrial numDistractors;
	
	
	public StimObjIdAssignerForRandTrials(TimeUtil globalTimeUtil, NumberOfDistractorsForRandTrial numDistractors) {
		super();
		this.globalTimeUtil = globalTimeUtil;
		this.numDistractors = numDistractors;
		
		assignStimObjIds();
	}
	
	private Rand<Long> stimObjIds = new Rand<Long>();
	
	private void assignStimObjIds() {
		stimObjIds.setSample(globalTimeUtil.currentTimeMicros());
		stimObjIds.setMatch(stimObjIds.getSample()+1);
		long prevId = stimObjIds.getMatch();
		for (int j=0; j<numDistractors.getNumQMDistractors();j++) {
			stimObjIds.getAllDistractors().add(prevId+1);
			stimObjIds.getQualitativeMorphDistractors().add(prevId+1);
			prevId++;
		}
		for (int j=0; j<numDistractors.getNumRandDistractors();j++) {
			stimObjIds.getAllDistractors().add(prevId+1);
			stimObjIds.getRandDistractors().add(prevId+1);
			prevId++;
		}
	}

	public Rand<Long> getStimObjIds() {
		return stimObjIds;
	}
	
}
