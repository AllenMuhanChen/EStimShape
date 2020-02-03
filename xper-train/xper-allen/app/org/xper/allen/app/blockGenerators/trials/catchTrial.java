package org.xper.allen.app.blockGenerators.trials;

public class catchTrial implements trial{
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
	int[] stimObjData = {1};
	int[] eStimObjData = {1};



}
