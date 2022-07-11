package org.xper.allen.nafc.blockgen;

/**
 * For 
 * @author r2_allen
 *
 */
public class HandicappedNAFCTrialParameters extends NAFCTrialParameters{
	private Lims distractorAdditionalDistanceLims;
	private Lims distractorAlphaLims;
	private Lims distractorScaleLims;
	
	public HandicappedNAFCTrialParameters(Lims sampleDistanceLims, Lims choiceDistanceLims, double size,
			double eyeWinSize, Lims distractorAdditionalDistanceLims, Lims distractorAlphaLims,
			Lims distractorScaleLims) {
		super(sampleDistanceLims, choiceDistanceLims, size, eyeWinSize);
		this.distractorAdditionalDistanceLims = distractorAdditionalDistanceLims;
		this.distractorAlphaLims = distractorAlphaLims;
		this.distractorScaleLims = distractorScaleLims;
	}

	public Lims getDistractorAdditionalDistanceLims() {
		return distractorAdditionalDistanceLims;
	}

	public void setDistractorAdditionalDistanceLims(Lims distractorAdditionalDistanceLims) {
		this.distractorAdditionalDistanceLims = distractorAdditionalDistanceLims;
	}

	public Lims getDistractorAlphaLims() {
		return distractorAlphaLims;
	}

	public void setDistractorAlphaLims(Lims distractorAlphaLims) {
		this.distractorAlphaLims = distractorAlphaLims;
	}


	public Lims getDistractorScaleLims() {
		return distractorScaleLims;
	}

	public void setDistractorScaleLims(Lims distractorScaleLims) {
		this.distractorScaleLims = distractorScaleLims;
	}
}