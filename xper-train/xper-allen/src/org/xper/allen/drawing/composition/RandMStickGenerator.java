package org.xper.allen.drawing.composition;

public class RandMStickGenerator extends AbstractMStickGenerator{


	public RandMStickGenerator(double maxImageDimensinDegrees) {
		super(maxImageDimensinDegrees);
		setMaxAttempts(5);
		makeAttemptsToGenerate();
	}

	@Override
	protected void attemptToGenerate() {
		mStick = new AllenMatchStick();
		mStick.setProperties(maxImageDimensionDegrees, "SHADE", 1.0);
		mStick.genMatchStickRand();
	}



}