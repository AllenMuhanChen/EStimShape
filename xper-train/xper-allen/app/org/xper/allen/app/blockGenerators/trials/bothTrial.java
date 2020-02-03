package org.xper.allen.app.blockGenerators.trials;

public class bothTrial implements trial{
	
	int[] stimObjData = {2};
	int[] eStimObjData = {2};
	
	public bothTrial() {
		//Empty Constructor
	}
	
	public bothTrial(int[] stimObjData, int[] estimObjData) {
		//stimObj Constructor
		this.eStimObjData = estimObjData;
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
