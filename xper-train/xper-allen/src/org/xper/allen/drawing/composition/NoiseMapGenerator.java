package org.xper.allen.drawing.composition;

import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricTrialGenerator;
import org.xper.allen.nafc.vo.NoiseParameters;

public abstract class NoiseMapGenerator {

	
	private static double[] noiseNormalizedPosition_PRE_JUNC = new double[] {0.5, 0.8};
	private static double[] noiseNormalizedPosition_POST_JUNC = new double[] {1.3, 2.0};
	private static double[] noiseNormalizedPosition_NONE = new double[] {0,0};
	
	protected long id;
	protected AllenMatchStick mStick;
	
	public NoiseMapGenerator(long id, AllenMatchStick mStick) {
		super();
		this.id = id;
		this.mStick = mStick;
	}
	
	public NoiseMapGenerator() {
	}

	protected NoiseParameters noiseParameters;
	protected String noiseMapPath;

	protected void generate() {
		assignParamsForNoiseMapGen();
		generateNoiseMap();
	}
	
	protected abstract void assignParamsForNoiseMapGen();
	protected abstract void generateNoiseMap();

	public String getNoiseMapPath() {
		return noiseMapPath;
	}

	public static double[] getNoiseNormalizedPosition_PRE_JUNC() {
		return noiseNormalizedPosition_PRE_JUNC;
	}

	public static double[] getNoiseNormalizedPosition_POST_JUNC() {
		return noiseNormalizedPosition_POST_JUNC;
	}

	public static double[] getNoiseNormalizedPosition_NONE() {
		return noiseNormalizedPosition_NONE;
	}

}