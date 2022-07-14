package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.nafc.blockgen.*;
import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;
import org.xper.allen.nafc.vo.MStickStimObjData;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;

public class RandTrialStimObjDataWriter extends NAFCStimObjDataWriter{

	private Rand<String> pngPaths;
	private Rand<Long> stimObjIds;
	private Rand<AllenMStickSpec> mStickSpecs;
	private Rand<Coordinates2D> coords;


	public RandTrialStimObjDataWriter(String noiseMapPath, AllenDbUtil dbUtil, NoisyTrialParameters trialParameters, Rand<String> pngPaths, Rand<Long> stimObjIds, Rand<AllenMStickSpec> mStickSpecs, Rand<Coordinates2D> coords) {
		super(noiseMapPath, dbUtil, trialParameters);
		this.pngPaths = pngPaths;
		this.stimObjIds = stimObjIds;
		this.mStickSpecs = mStickSpecs;
		this.coords = coords;
	}

	@Override
	protected void writeDistractorSpecs() {
		int indx=0;
		for(Long stimObjId : stimObjIds.getQualitativeMorphDistractors()) {
			NoisyPngSpecWriter distractorSpecWriter = NoisyPngSpecWriter.createWithoutNoiseMap(
					getCoords().getQualitativeMorphDistractors().get(indx), getPngPaths().getQualitativeMorphDistractors().get(indx),trialParameters.getSize());
			distractorSpecWriter.writeSpec();
			NoisyPngSpec distractorSpec = distractorSpecWriter.getSpec();
			MStickStimObjData distractorMStickObjData = new MStickStimObjData("Qualitative Morph Distractor", getmStickSpecs().getMatch());
			dbUtil.writeStimObjData(stimObjId, distractorSpec.toXml(), distractorMStickObjData.toXml());
			indx++;
		}

		indx=0;
		for(Long stimObjId : stimObjIds.getRandDistractors()) {
			NoisyPngSpecWriter distractorSpecWriter = NoisyPngSpecWriter.createWithoutNoiseMap(
					getCoords().getRandDistractors().get(indx), getPngPaths().getRandDistractors().get(indx),trialParameters.getSize());
			distractorSpecWriter.writeSpec();
			NoisyPngSpec distractorSpec = distractorSpecWriter.getSpec();
			MStickStimObjData distractorMStickObjData = new MStickStimObjData("Rand Distractor", getmStickSpecs().getMatch());
			dbUtil.writeStimObjData(stimObjId, distractorSpec.toXml(), distractorMStickObjData.toXml());
			indx++;
		}
		
	}


	@Override
	protected Rand<String> getPngPaths(){
		return pngPaths;
	}

	@Override
	protected Rand<AllenMStickSpec> getmStickSpecs(){
		return mStickSpecs;
	}

	@Override
	protected Rand<Coordinates2D> getCoords(){
		return coords;
	}

	@Override
	protected Rand<Long> getStimObjIds(){
		return stimObjIds;
	}



}
