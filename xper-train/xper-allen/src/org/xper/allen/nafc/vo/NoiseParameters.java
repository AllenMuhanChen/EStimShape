package org.xper.allen.nafc.vo;

import java.util.HashMap;
import java.util.Map;

public class NoiseParameters {

	NoiseForm noiseForm = new NoiseForm();
	double[] noiseChanceBounds;
	
	
	public NoiseParameters(NoiseType noiseType, double[] normalizedPositionBounds, double[] noiseChanceBounds) {
		super();
		this.noiseChanceBounds = noiseChanceBounds;
		this.noiseForm = new NoiseForm(noiseType, normalizedPositionBounds);
	}
	
	public NoiseParameters(NoiseForm noiseForm, double[] noiseChanceBounds) {
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
	public double[] getNormalizedPositionBounds() {
		return noiseForm.getNormalizedPositionBounds();
	}
	public void setNormalizedPositionBounds(double[] normalizedPositionBounds) {
		this.noiseForm.setNormalizedPositionBounds(normalizedPositionBounds);
	}
	public double[] getNoiseChanceBounds() {
		return noiseChanceBounds;
	}
	public void setNoiseChanceBounds(double[] noiseChanceBounds) {
		this.noiseChanceBounds = noiseChanceBounds;
	}
}
