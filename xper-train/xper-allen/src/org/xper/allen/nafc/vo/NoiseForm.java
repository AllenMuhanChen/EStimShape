package org.xper.allen.nafc.vo;

import org.xper.allen.drawing.composition.noisy.NoisePositions;

public class NoiseForm {
	private NoiseType noiseType;
	private NoisePositions normalizedPositionBounds;

	public NoiseForm() {
	}

	public NoiseForm(NoiseType noiseType, NoisePositions normalizedPositionBounds) {
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

	public NoisePositions getNormalizedPositionBounds() {
		return normalizedPositionBounds;
	}

	public void setNormalizedPositionBounds(NoisePositions normalizedPositionBounds) {
		this.normalizedPositionBounds = normalizedPositionBounds;
	}
}