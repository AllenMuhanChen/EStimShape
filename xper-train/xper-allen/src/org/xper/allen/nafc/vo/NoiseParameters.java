package org.xper.allen.nafc.vo;

public class NoiseParameters {
	
	NoiseType noiseType;
	double[] normalizedPositionBounds; 
	double[] noiseChanceBounds;
	
	
	public NoiseParameters(NoiseType noiseType, double[] normalizedPositionBounds, double[] noiseChanceBounds) {
		super();
		this.noiseType = noiseType;
		this.normalizedPositionBounds = normalizedPositionBounds;
		this.noiseChanceBounds = noiseChanceBounds;
	}
	
	public NoiseParameters(NoiseType noiseType, double[] noiseChanceBounds) {
		super();
		this.noiseType = noiseType;
		this.noiseChanceBounds = noiseChanceBounds;
	}
	
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
