package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.nafc.blockgen.NAFCCoordinates;
import org.xper.allen.nafc.blockgen.NAFCMStickSpecs;
import org.xper.allen.nafc.blockgen.NAFCPaths;
import org.xper.allen.nafc.blockgen.NoisyPngSpecWriter;
import org.xper.allen.nafc.blockgen.StimObjIds;
import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;
import org.xper.allen.nafc.vo.MStickStimObjData;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.allen.util.AllenDbUtil;

public class RandTrialStimObjDataWriter extends NAFCStimObjDataWriter{

	StimObjIdsForRandTrial stimObjIds;
	public RandTrialStimObjDataWriter(int numChoices, NAFCPaths pngPaths, String noiseMapPath, AllenDbUtil dbUtil,
			NAFCMStickSpecs mStickSpecs, NoisyTrialParameters trialParameters, NAFCCoordinates coords,
			StimObjIdsForRandTrial stimObjIds) {
		super(numChoices, pngPaths, noiseMapPath, dbUtil, mStickSpecs, trialParameters, coords);
		this.stimObjIds = stimObjIds;
	}



	@Override
	protected void writeDistractorSpecs() {
		int indx=0;
		for(Long stimObjId : stimObjIds.getQmDistractorIds()) {
			NoisyPngSpecWriter distractorSpecWriter = NoisyPngSpecWriter.createWithoutNoiseMap(
					coords.getDistractorCoords().get(indx), pngPaths.getDistractorsPaths().get(indx),trialParameters.getSize());
			distractorSpecWriter.writeSpec();
			NoisyPngSpec distractorSpec = distractorSpecWriter.getSpec();
			MStickStimObjData distractorMStickObjData = new MStickStimObjData("Qualitative Morph Distractor", mStickSpecs.getMatchMStickSpec());
			dbUtil.writeStimObjData(stimObjId, distractorSpec.toXml(), distractorMStickObjData.toXml());
			indx++;
		}
		
		int numQMDistractors = stimObjIds.getQmDistractorIds().size();
		indx=0;
		for(Long stimObjId : stimObjIds.getRandDistractorIds()) {
			int allDistractorsIndx = numQMDistractors+indx;
			NoisyPngSpecWriter distractorSpecWriter = NoisyPngSpecWriter.createWithoutNoiseMap(
					coords.getDistractorCoords().get(allDistractorsIndx), pngPaths.getDistractorsPaths().get(allDistractorsIndx),trialParameters.getSize());
			distractorSpecWriter.writeSpec();
			NoisyPngSpec distractorSpec = distractorSpecWriter.getSpec();
			MStickStimObjData distractorMStickObjData = new MStickStimObjData("Rand Distractor", mStickSpecs.getMatchMStickSpec());
			dbUtil.writeStimObjData(stimObjId, distractorSpec.toXml(), distractorMStickObjData.toXml());
			indx++;
		}
		
	}
}
