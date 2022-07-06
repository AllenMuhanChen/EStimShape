package org.xper.allen.nafc.blockgen;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;

public class NAFCAllenMStickSpecs {
	private AllenMStickSpec sampleMStickSpec;
	private AllenMStickSpec matchMStickSpec;
	private List<AllenMStickSpec> distractorsMStickSpecs;

	public NAFCAllenMStickSpecs() {
		this.distractorsMStickSpecs = new LinkedList<AllenMStickSpec>();
	}

	public void addDistractorSpec(AllenMStickSpec spec) {
		this.distractorsMStickSpecs.add(spec);
	}


	public AllenMStickSpec getSampleMStickSpec() {
		return sampleMStickSpec;
	}

	public void setSampleMStickSpec(AllenMStickSpec sampleMStickSpec) {
		this.sampleMStickSpec = sampleMStickSpec;
	}

	public AllenMStickSpec getMatchMStickSpec() {
		return matchMStickSpec;
	}

	public void setMatchMStickSpec(AllenMStickSpec matchMStickSpec) {
		this.matchMStickSpec = matchMStickSpec;
	}

	public List<AllenMStickSpec> getDistractorsMStickSpecs() {
		return distractorsMStickSpecs;
	}

	public void setDistractorsMStickSpecs(List<AllenMStickSpec> distractorsMStickSpecs) {
		this.distractorsMStickSpecs = distractorsMStickSpecs;
	}


}