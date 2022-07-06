package org.xper.allen.nafc.blockgen;

import java.util.List;

import org.xper.allen.drawing.composition.AllenMatchStick;

public class NAFCAllenMatchSticks {
	private AllenMatchStick sampleMStick;
	private AllenMatchStick matchMStick;
	private List<AllenMatchStick> distractorMSticks;

	public NAFCAllenMatchSticks() {
	}

	public void addDistractorMStick(AllenMatchStick mStick) {
		distractorMSticks.add(mStick);
	}
	
	public AllenMatchStick getSampleMStick() {
		return sampleMStick;
	}

	public void setSampleMStick(AllenMatchStick sampleMStick) {
		this.sampleMStick = sampleMStick;
	}

	public AllenMatchStick getMatchMStick() {
		return matchMStick;
	}

	public void setMatchMStick(AllenMatchStick matchMStick) {
		this.matchMStick = matchMStick;
	}

	public List<AllenMatchStick> getDistractorMSticks() {
		return distractorMSticks;
	}

	public void setDistractorMSticks(List<AllenMatchStick> distractorMSticks) {
		this.distractorMSticks = distractorMSticks;
	}
}