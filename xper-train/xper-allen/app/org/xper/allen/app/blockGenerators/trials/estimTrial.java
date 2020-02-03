package org.xper.allen.app.blockGenerators.trials;

public class estimTrial implements trial{
	
	int[] stimObjData = {1};
	int[] eStimObjData = {2};
	
	public estimTrial() {
	}
	
	public estimTrial(int[] estimObjData) {
		this.eStimObjData = estimObjData;
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
