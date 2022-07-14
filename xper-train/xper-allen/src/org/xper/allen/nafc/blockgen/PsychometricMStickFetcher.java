package org.xper.allen.nafc.blockgen;

import java.util.LinkedList;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.nafc.blockgen.psychometric.Psychometric;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricMStickSpecs;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricMSticks;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricPaths;


public class PsychometricMStickFetcher {
	
	AbstractMStickPngTrialGenerator gen;
	
	Psychometric<AllenMStickSpec> mStickSpecs = new Psychometric<AllenMStickSpec>();
	Psychometric<AllenMatchStick>matchSticks = new Psychometric<AllenMatchStick>();
	Psychometric<String> specPaths = new Psychometric<String>();
	
	public PsychometricMStickFetcher(AbstractMStickPngTrialGenerator gen, Psychometric<String> specPaths) {
		super();
		this.gen = gen;
		this.specPaths = specPaths;
		
		fetchMSticksAndSpecs();
	}

	private void fetchMSticksAndSpecs() {
		matchSticks.setSample(fetchMStick(specPaths.getSample()));
		mStickSpecs.setSample(fetchMStickSpec(matchSticks.getSample()));
		
		matchSticks.setMatch(fetchMStick(specPaths.getMatch()));
		mStickSpecs.setMatch(fetchMStickSpec(matchSticks.getMatch()));
		
		for (String distractorSpecPath : specPaths.getPsychometricDistractors()) {
			AllenMatchStick psychometricDistractorMStick = fetchMStick(distractorSpecPath);
			matchSticks.addPsychometricDistractor(psychometricDistractorMStick);
			mStickSpecs.addPsychometricDistractor(fetchMStickSpec(psychometricDistractorMStick));
		}
	}
	
	private AllenMatchStick fetchMStick(String specPath) {
		AllenMatchStick ams = new AllenMatchStick();
		gen.setProperties(ams);
		ams.genMatchStickFromFile(specPath);
		return ams;
	}
	
	private AllenMStickSpec fetchMStickSpec(AllenMatchStick mStick) {
		AllenMStickSpec mStickSpec = new AllenMStickSpec();
		mStickSpec.setMStickInfo(mStick);
		return mStickSpec;
	}

	public Psychometric<AllenMStickSpec> getmStickSpecs() {
		return mStickSpecs;
	}

	public Psychometric<AllenMatchStick> getMatchSticks() {
		return matchSticks;
	}





	
	
}
