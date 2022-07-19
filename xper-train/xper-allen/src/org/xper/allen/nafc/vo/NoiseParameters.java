package org.xper.allen.nafc.vo;

import org.xper.allen.drawing.composition.noisy.NoisePositions;
import org.xper.allen.nafc.blockgen.Lims;

public class NoiseParameters {

	NoiseForm noiseForm = new NoiseForm();
	Lims noiseChanceBounds;
	
	
	public NoiseParameters(NoiseType noiseType, NoisePositions normalizedPositionBounds, Lims noiseChanceBounds) {
		super();
		this.noiseChanceBounds = noiseChanceBounds;
		this.noiseForm = new NoiseForm(noiseType, normalizedPositionBounds);
	}
	
	public NoiseParameters(NoiseForm noiseForm, Lims noiseChanceBounds) {
		super();
		this.noiseForm = noiseForm;
		this.noiseChanceBounds = noiseChanceBounds;
	}

	public NoiseType getNoiseType() {
		return noiseForm.getNoiseType();
	}
	public void setNoiseType(NoiseType noiseType) {
		this.noiseForm.setNoiseType(noiseType);
	}
	public NoisePositions getNormalizedPositionBounds() {
		return noiseForm.getNormalizedPositionBounds();
	}
	public void setNormalizedPositionBounds(NoisePositions normalizedPositionBounds) {
		this.noiseForm.setNormalizedPositionBounds(normalizedPositionBounds);
	}
	public Lims getNoiseChanceBounds() {
		return noiseChanceBounds;
	}
	public void setNoiseChanceBounds(Lims noiseChanceBounds) {
		this.noiseChanceBounds = noiseChanceBounds;
	}
}
