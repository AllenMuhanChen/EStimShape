package org.xper.allen.drawing.composition;

import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

public class RandMStickGenerator extends AbstractMStickGenerator{


	public RandMStickGenerator(double maxImageDimensinDegrees) {
		super(maxImageDimensinDegrees);
		setMaxAttempts(100);
		makeAttemptsToGenerate();
	}

	@Override
	protected void attemptToGenerate() {
		mStick = new AllenMatchStick();
		mStick.setProperties(maxImageDimensionDegrees);
		mStick.genMatchStickRand();
	}

	
	
}
