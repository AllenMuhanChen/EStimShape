package org.xper.allen.nafc.blockgen.psychometric;

import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.nafc.blockgen.NAFCMStickSpecs;

public class PsychometricMStickSpecs extends NAFCMStickSpecs{
	private List<AllenMStickSpec> psychometricDistractorMStickSpecs = new LinkedList<>();
	private List<AllenMStickSpec> randDistractorMStickSpecs = new LinkedList<>();
	
	public PsychometricMStickSpecs(List<AllenMStickSpec> psychometricDistractorMStickSpecs,
			List<AllenMStickSpec> randDistractorMStickSpecs) {
		super();
		this.psychometricDistractorMStickSpecs = psychometricDistractorMStickSpecs;
		this.randDistractorMStickSpecs = randDistractorMStickSpecs;
	}
	
	public PsychometricMStickSpecs() {
	}
	public List<AllenMStickSpec> getPsychometricDistractorMStickSpecs() {
		return psychometricDistractorMStickSpecs;
	}
	public void setPsychometricDistractorMStickSpecs(List<AllenMStickSpec> psychometricDistractorMStickSpecs) {
		this.psychometricDistractorMStickSpecs = psychometricDistractorMStickSpecs;
	}
	public List<AllenMStickSpec> getRandDistractorMStickSpecs() {
		return randDistractorMStickSpecs;
	}
	public void setRandDistractorMStickSpecs(List<AllenMStickSpec> randDistractorMStickSpecs) {
		this.randDistractorMStickSpecs = randDistractorMStickSpecs;
	}
	
}
