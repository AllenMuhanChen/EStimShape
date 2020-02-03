package org.xper.allen.app.blockGenerators.trials;

public class visualTrial extends Trial{
	
	int[] stimObjData = {2};
	int[] eStimObjData = {1};
	
	public visualTrial() {
		//Empty Constructor
	}
	
	public visualTrial(int[] stimObjData) {
		//stimObj Constructor
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
