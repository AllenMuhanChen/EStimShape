package org.xper.allen.nafc.vo;

public class NoiseForm {
	private NoiseType noiseType;
	private double[] normalizedPositionBounds;

	public NoiseForm() {
	}

	public NoiseForm(NoiseType noiseType, double[] normalizedPositionBounds) {
		super();
		this.noiseType = noiseType;
		this.normalizedPositionBounds = normalizedPositionBounds;
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
}