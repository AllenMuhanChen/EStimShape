package org.xper.allen.nafc.blockgen.psychometric;

import java.util.List;

public class PsychometricIds {
	public long setId;
	public int stimId;
	public List<Integer> allStimIds;
	public PsychometricIds(long setId, int stimId, List<Integer> allStimIds) {
		super();
		this.setId = setId;
		this.stimId = stimId;
		this.allStimIds = allStimIds;
	}

}