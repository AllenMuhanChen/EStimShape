package org.xper.allen.nafc.blockgen.psychometric;

import java.util.ArrayList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.blockgen.NAFCMStickSpecs;
import org.xper.allen.nafc.blockgen.NAFCCoordinates;
import org.xper.allen.nafc.blockgen.NAFCPaths;
import org.xper.allen.nafc.blockgen.NoisyPngSpecWriter;
import org.xper.allen.nafc.blockgen.StimObjIdsForMixedPsychometricAndRand;
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
public class PsychometricStimObjSpecWriter{

	//Needed for StimObjSpec writing (Input Vars)
	int numChoices;
	NAFCPaths pngPaths;
	StimObjIdsForMixedPsychometricAndRand stimObjIds;
	String noiseMapPath;
	AllenDbUtil dbUtil;
	NAFCMStickSpecs mStickSpecs = new NAFCMStickSpecs();
	NoisyTrialParameters trialParameters; //input
	NAFCCoordinates coords;

	public PsychometricStimObjSpecWriter(int numChoices, NAFCPaths pngPaths,
			StimObjIdsForMixedPsychometricAndRand stimObjIds, String noiseMapPath, AllenDbUtil dbUtil,
			NAFCMStickSpecs mStickSpecs,
			NoisyTrialParameters trialParameters, NAFCCoordinates coords) {
		super();
		this.numChoices = numChoices;
		this.pngPaths = pngPaths;
		this.stimObjIds = stimObjIds;
		this.noiseMapPath = noiseMapPath;
		this.dbUtil = dbUtil;
		this.mStickSpecs = mStickSpecs;
		this.trialParameters = trialParameters;
		this.coords = coords;
	}

	public void writeStimObjId() {
		writeSampleSpec();
		writeMatchSpec();
		writeDistractorSpecs();
	}

	private void writeSampleSpec() {
		NoisyPngSpecWriter sampleSpecWriter = NoisyPngSpecWriter.createWithNoiseMap(
				coords.getSampleCoords(),
				pngPaths.getSamplePath(), noiseMapPath,
				trialParameters.getSize());

		sampleSpecWriter.writeSpec();
		NoisyPngSpec sampleSpec = sampleSpecWriter.getSpec();
		
		
		MStickStimObjData sampleMStickObjData = new MStickStimObjData("Sample", mStickSpecs.getSampleMStickSpec());
		dbUtil.writeStimObjData(stimObjIds.getSampleId(), sampleSpec.toXml(), sampleMStickObjData.toXml());
	}

	private void writeMatchSpec() {
		NoisyPngSpecWriter matchSpecWriter = NoisyPngSpecWriter.createWithoutNoiseMap(
				coords.getMatchCoords(),
				pngPaths.getMatchPath(),
				trialParameters.getSize());
		matchSpecWriter.writeSpec();
		NoisyPngSpec matchSpec = matchSpecWriter.getSpec();

		MStickStimObjData matchMStickObjData = new MStickStimObjData("Match", mStickSpecs.getMatchMStickSpec());
		dbUtil.writeStimObjData(stimObjIds.getMatchId(), matchSpec.toXml(), matchMStickObjData.toXml());
	}

	private void writeDistractorSpecs() {
		int indx=0;
		for(Coordinates2D coord:coords.getDistractorCoords()) {
			NoisyPngSpecWriter distractorSpecWriter = NoisyPngSpecWriter.createWithoutNoiseMap(
					coord, pngPaths.getDistractorsPaths().get(indx),trialParameters.getSize());
			distractorSpecWriter.writeSpec();
			NoisyPngSpec distractorSpec = distractorSpecWriter.getSpec();
			MStickStimObjData distractorMStickObjData = new MStickStimObjData("Distractor", mStickSpecs.getMatchMStickSpec());
			dbUtil.writeStimObjData(stimObjIds.getAllDistractorsIds().get(indx), distractorSpec.toXml(), distractorMStickObjData.toXml());
			indx++;
		}
	}



}

