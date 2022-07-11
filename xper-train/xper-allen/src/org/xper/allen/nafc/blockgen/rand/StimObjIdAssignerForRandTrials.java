package org.xper.allen.nafc.blockgen.rand;

import org.xper.time.TimeUtil;

public class StimObjIdAssignerForRandTrials{
	private TimeUtil globalTimeUtil;
	private NumberOfDistractorsByMorphType numDistractors;
	
	
	public StimObjIdAssignerForRandTrials(TimeUtil globalTimeUtil, NumberOfDistractorsByMorphType numDistractors) {
		super();
		this.globalTimeUtil = globalTimeUtil;
		this.numDistractors = numDistractors;
		
		assignStimObjIds();
	}
	
	private StimObjIdsForRandTrial stimObjIds = new StimObjIdsForRandTrial(); 
	
	private void assignStimObjIds() {
		stimObjIds.setSampleId(globalTimeUtil.currentTimeMicros());
		stimObjIds.setMatchId(stimObjIds.getSampleId()+1);
		long prevId = stimObjIds.getMatchId();
		for (int j=0; j<numDistractors.getNumQMDistractors();j++) {
			stimObjIds.getAllDistractorIds().add(prevId+1);
			stimObjIds.getQmDistractorIds().add(prevId+1);
			prevId++;
		}
		for (int j=0; j<numDistractors.getNumRandDistractors();j++) {
			stimObjIds.getAllDistractorIds().add(prevId+1);
			stimObjIds.getRandDistractorIds().add(prevId+1);
			prevId++;
		}
	}

	public StimObjIdsForRandTrial getStimObjIds() {
		return stimObjIds;
	}
	
}
