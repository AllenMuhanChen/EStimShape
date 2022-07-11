package org.xper.allen.drawing.composition;

public abstract class AbstractMStickGenerator implements MStickGenerator{

	protected boolean successful;
	protected AllenMatchStick mStick = new AllenMatchStick();

	public AbstractMStickGenerator() {
		super();
	}

	protected void fail(String step, int nTries) {
		throw new MaxAttemptsReachedException(step, nTries);
	}

	@Override
	public boolean isSuccessful() {
		return successful;
	}

	@Override
	public AllenMatchStick getmStick() {
		if (isSuccessful()) return mStick;
		else throw new MStickGenerationException();
	}
	
	public AllenMatchStick tryGenerate() {
		try {
			attemptGenerate();
			if(isSuccessful()) {
				return getmStick();
			} else {
				throw new MStickGenerationException();
			}
		}catch (Exception e) {
//			e.printStackTrace();
			throw new MStickGenerationException();
			
		}
	}

}