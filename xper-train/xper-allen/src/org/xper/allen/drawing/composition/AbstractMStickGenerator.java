package org.xper.allen.drawing.composition;

public abstract class AbstractMStickGenerator{

	private static int maxAttempts = 5;

	protected boolean successful;
	protected AllenMatchStick mStick = new AllenMatchStick();
	protected AllenMStickSpec mStickSpec = new AllenMStickSpec();
	protected double maxImageDimensionDegrees;

	public AbstractMStickGenerator(double maxImageDimensionDegrees) {
		super();
		this.maxImageDimensionDegrees = maxImageDimensionDegrees;
	}

	public AbstractMStickGenerator() {
		super();
	}

	protected void
	makeAttemptsToGenerate() {
		int nTries = 0;

		while (nTries<maxAttempts) {
			try {
				attemptToGenerate();
				successful = true;
				break;
			} catch (Exception e) {
				nTries++;
				successful=false;
			}
		}

		if (nTries>=maxAttempts) {
			fail("", nTries);
		}

	}

	public AllenMStickSpec getMStickSpec() {
		mStickSpec = new AllenMStickSpec();
		mStickSpec.setMStickInfo(mStick, true);
		return mStickSpec;
	}

	public AllenMatchStick getMStick() {
		if (isSuccessful()) return mStick;
		else throw new MStickGenerationException();
	}

	protected abstract void attemptToGenerate();

	protected void fail(String step, int nTries) {
		throw new MaxAttemptsReachedException(step, nTries);
	}

	public boolean isSuccessful() {
		return successful;
	}




	protected static void setMaxAttempts(int maxAttempts) {
		AbstractMStickGenerator.maxAttempts = maxAttempts;
	}






}