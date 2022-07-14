package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.nafc.blockgen.NoisyPngSpecWriter;
import org.xper.allen.nafc.blockgen.rand.NAFCStimObjDataWriter;
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

	private Psychometric<String> pngPaths;
	private Psychometric<Long> stimObjIds;
	private Psychometric<AllenMStickSpec> mStickSpecs;
	private Psychometric<Coordinates2D> coords;

	public PsychometricStimObjDataWriter(String noiseMapPath, AllenDbUtil dbUtil, NoisyTrialParameters trialParameters, Psychometric<String> pngPaths, Psychometric<Long> stimObjIds, Psychometric<AllenMStickSpec> mStickSpecs, Psychometric<Coordinates2D> coords) {
		super(noiseMapPath, dbUtil, trialParameters);
		this.pngPaths = pngPaths;
		this.stimObjIds = stimObjIds;
		this.mStickSpecs = mStickSpecs;
		this.coords = coords;
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
					getCoords().getPsychometricDistractors().get(indx), getPngPaths().getPsychometricDistractors().get(indx),trialParameters.getSize());
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
					getCoords().getRandDistractors().get(indx), getPngPaths().getRandDistractors().get(indx),trialParameters.getSize());
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

	@Override
	protected Psychometric<String> getPngPaths(){
		return pngPaths;
	}

	@Override
	protected Psychometric<AllenMStickSpec> getmStickSpecs(){
		return mStickSpecs;
	}

	@Override
	protected Psychometric<Coordinates2D> getCoords(){
		return coords;
	}

	@Override
	protected Psychometric<Long> getStimObjIds(){
		return stimObjIds;
	}


}

