package org.xper.allen.app.blockGenerators.trials;

public class visualTrial implements trial{
	
	int[] stimObjData = {2};
	int[] eStimObjData = {1};
	
	public visualTrial(int[] stimObjData) {
		this.stimObjData = stimObjData;
	}
	
	public int[] getStimObjData() {
		return stimObjData;
	}
	public void setStimObjData(int[] stimObjData) {
		this.stimObjData = stimObjData;
	}
	public int[] getEStimObjData() {
		return eStimObjData;
	}
	public void setEStimObjData(int[] eStimObjData) {
		this.eStimObjData = eStimObjData;
	}

}
