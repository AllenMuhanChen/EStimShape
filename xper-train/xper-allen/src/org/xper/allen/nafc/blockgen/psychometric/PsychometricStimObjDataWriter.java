package org.xper.allen.nafc.blockgen.psychometric;

import java.util.ArrayList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.blockgen.NAFCMStickSpecs;
import org.xper.allen.nafc.blockgen.NoisyPngSpecWriter;
import org.xper.allen.nafc.blockgen.StimObjIdsForMixedPsychometricAndRand;
import org.xper.allen.nafc.blockgen.rand.NAFCStimObjDataWriter;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.nafc.vo.MStickStimObjData;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;

/**
 * Handles writing specs to database
 * @author r2_allen
 *
 */
public class PsychometricStimObjDataWriter extends NAFCStimObjDataWriter{



	private Psychometric<Long> stimObjIds;
	private Psychometric<AllenMStickSpec> mStickSpecs;
	
	public PsychometricStimObjDataWriter(int numChoices, Psychometric<String> pngPaths, String noiseMapPath, AllenDbUtil dbUtil,
			Psychometric<AllenMStickSpec> mStickSpecs, NoisyTrialParameters trialParameters, Psychometric<Coordinates2D> coords,
			Psychometric<Long> stimObjIds) {
		super(numChoices, pngPaths, noiseMapPath, dbUtil, mStickSpecs, trialParameters, coords, stimObjIds);
		this.stimObjIds = stimObjIds;
		this.mStickSpecs = mStickSpecs;
	}

	@Override
	protected void writeDistractorSpecs() {
		writePsychometricDistractors();
		writeRandDistractors();
	}


	private void writePsychometricDistractors() {
		int indx=0;
		for(Long stimObjId : stimObjIds.getPsychometricDistractors()) {
			NoisyPngSpecWriter distractorSpecWriter = NoisyPngSpecWriter.createWithoutNoiseMap(
					coords.getPsychometricDistractors().get(indx), pngPaths.getPsychometricDistractors().get(indx),trialParameters.getSize());
			distractorSpecWriter.writeSpec();
			NoisyPngSpec distractorSpec = distractorSpecWriter.getSpec();
			MStickStimObjData distractorMStickObjData = new MStickStimObjData("Psychometric Distractor", mStickSpecs.getPsychometricDistractors().get(indx));
			dbUtil.writeStimObjData(stimObjId, distractorSpec.toXml(), distractorMStickObjData.toXml());
			indx++;
		}
	}

	private void writeRandDistractors() {
		int indx;
		indx=0;
		for(Long stimObjId : stimObjIds.getRandDistractors()) {
			NoisyPngSpecWriter distractorSpecWriter = NoisyPngSpecWriter.createWithoutNoiseMap(
					coords.getRandDistractors().get(indx), pngPaths.getRandDistractors().get(indx),trialParameters.getSize());
			distractorSpecWriter.writeSpec();
			NoisyPngSpec distractorSpec = distractorSpecWriter.getSpec();
			MStickStimObjData distractorMStickObjData = new MStickStimObjData("Rand Distractor", mStickSpecs.getRandDistractors().get(indx));
			dbUtil.writeStimObjData(stimObjId, distractorSpec.toXml(), distractorMStickObjData.toXml());
			indx++;
		}
	}

	
	protected void setStimObjIds(Psychometric<Long> stimObjIds) {
		this.stimObjIds = stimObjIds;
	}

}

