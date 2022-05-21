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
	
	public NoiseType getNoiseType() {
		return noiseType;
	}
	public void setNoiseType(NoiseType noiseType) {
		this.noiseType = noiseType;
	}
	public double[] getNormalizedPositionBounds() {
		return normalizedPositionBounds;
	}
	public void setNormalizedPositionBounds(double[] normalizedPositionBounds) {
		this.normalizedPositionBounds = normalizedPositionBounds;
	}
	public double[] getNoiseChanceBounds() {
		return noiseChanceBounds;
	}
	public void setNoiseChanceBounds(double[] noiseChanceBounds) {
		this.noiseChanceBounds = noiseChanceBounds;
	}
}
