package org.xper.allen.drawing.composition;

import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

public class RandMStickGenerator extends AbstractMStickGenerator{


	public RandMStickGenerator(AbstractMStickPngTrialGenerator generator) {
		super(generator);
		setMaxAttempts(100);
		makeAttemptsToGenerate();
	}

	@Override
	protected void attemptToGenerate() {
		mStick = new AllenMatchStick();
		generator.setProperties(mStick);
		mStick.genMatchStickRand();
	}

	
	
}
