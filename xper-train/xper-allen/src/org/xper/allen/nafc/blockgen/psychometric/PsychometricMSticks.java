package org.xper.allen.nafc.blockgen.psychometric;

import java.util.ArrayList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.nafc.blockgen.NAFCMSticks;

public class PsychometricMSticks extends NAFCMSticks{
	private List<AllenMatchStick> psychometricDistractorMSticks = new ArrayList<AllenMatchStick>();
	private List<AllenMatchStick> randDistractorMSticks = new ArrayList<AllenMatchStick>();
	
	public PsychometricMSticks(List<AllenMatchStick> psychometricDistractorMSticks,
			List<AllenMatchStick> randDistractorMSticks) {
		super();
		this.psychometricDistractorMSticks = psychometricDistractorMSticks;
		this.randDistractorMSticks = randDistractorMSticks;
	}

	public PsychometricMSticks() {
		
	}
	
	public void addRandDistractorMStick(AllenMatchStick mStick) {
		randDistractorMSticks.add(mStick);
		addToAllDistractors(mStick);
	}
	
	public void addPsychometricDistractorMStick(AllenMatchStick mStick) {
		psychometricDistractorMSticks.add(mStick);
		addToAllDistractors(mStick);
	}
	
	private void addToAllDistractors(AllenMatchStick mStick) {
		if(!getDistractorMSticks().contains(mStick))
			getDistractorMSticks().add(mStick);
	}
	
	
	public List<AllenMatchStick> getPsychometricDistractorMSticks() {
		return psychometricDistractorMSticks;
	}

	public void setPsychometricDistractorMSticks(List<AllenMatchStick> psychometricDistractorMSticks) {
		this.psychometricDistractorMSticks = psychometricDistractorMSticks;
	}

	public List<AllenMatchStick> getRandDistractorMSticks() {
		return randDistractorMSticks;
	}

	public void setRandDistractorMSticks(List<AllenMatchStick> randDistractorMSticks) {
		this.randDistractorMSticks = randDistractorMSticks;
	}


	
	
}
