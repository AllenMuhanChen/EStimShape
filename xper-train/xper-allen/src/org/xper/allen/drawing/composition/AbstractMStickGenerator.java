package org.xper.allen.drawing.composition;

import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

public abstract class AbstractMStickGenerator{

	private static int maxAttempts = 5;
	
	protected AbstractMStickPngTrialGenerator generator;
	
	protected boolean successful;
	protected AllenMatchStick mStick = new AllenMatchStick();
	protected AllenMStickSpec mStickSpec = new AllenMStickSpec();

	public AbstractMStickGenerator() {
		super();
		
	}

	public AbstractMStickGenerator(AbstractMStickPngTrialGenerator generator) {
		super();
		this.generator = generator;
	}

	protected void makeAttemptsToGenerate() {
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
		mStickSpec.setMStickInfo(mStick);
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