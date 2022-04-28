package org.xper.allen.nafc.vo;

public class NoiseData {
	public NoiseData(NoiseType noiseType, double[] normalizedPositionBounds, double[] noiseChanceBounds) {
		super();
		this.noiseType = noiseType;
		this.normalizedPositionBounds = normalizedPositionBounds;
		this.noiseChanceBounds = noiseChanceBounds;
	}
	NoiseType noiseType;
	double[] normalizedPositionBounds; 
	double[] noiseChanceBounds;
}
