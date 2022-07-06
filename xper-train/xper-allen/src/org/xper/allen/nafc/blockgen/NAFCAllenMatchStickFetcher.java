package org.xper.allen.nafc.blockgen;

import java.util.LinkedList;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;


public class NAFCAllenMatchStickFetcher {
	
	AbstractMStickPngTrialGenerator gen;
	
	NAFCAllenMStickSpecs mStickSpecs = new NAFCAllenMStickSpecs();
	NAFCAllenMatchSticks matchSticks = new NAFCAllenMatchSticks();
	NAFCPaths specPaths;
	
	public NAFCAllenMatchStickFetcher(AbstractMStickPngTrialGenerator gen, NAFCPaths specPaths) {
		super();
		this.gen = gen;
		this.specPaths = specPaths;
	}

	public void fetchMSticksAndSpecs() {
		matchSticks.setSampleMStick(fetchMStick(specPaths.getSamplePath()));
		mStickSpecs.setSampleMStickSpec(fetchMStickSpec(matchSticks.getSampleMStick()));
		
		matchSticks.setMatchMStick(fetchMStick(specPaths.getMatchPath()));
		mStickSpecs.setMatchMStickSpec(fetchMStickSpec(matchSticks.getMatchMStick()));
		
		for (String distractorSpecPath : specPaths.getDistractorsPaths()) {
			AllenMatchStick distractorMStick = fetchMStick(distractorSpecPath);
			matchSticks.addDistractorMStick(distractorMStick);
			mStickSpecs.addDistractorSpec(fetchMStickSpec(distractorMStick));
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

	public NAFCAllenMStickSpecs getmStickSpecs() {
		return mStickSpecs;
	}

	public NAFCAllenMatchSticks getMatchSticks() {
		return matchSticks;
	}


	
	
}
