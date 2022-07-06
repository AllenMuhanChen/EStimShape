package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.png.ImageDimensions;
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
public class NoisyMStickPngPsychometricDBWriter{

	NoisyMStickPngPsychometricTrialGenData trialGenData;
	int numChoices;
	NAFCPaths pngPaths;
	StimObjIdsForMixedPsychometricAndRand stimObjIds;
	String noiseMapPath;
	AllenDbUtil dbUtil;

	Coordinates2D sampleCoords;
	Coordinates2D matchCoords;
	ArrayList<Coordinates2D> distractorsCoords;
	private long[] eStimObjData;
	private RewardPolicy rewardPolicy;
	private int[] rewardList;
	private List<Coordinates2D> targetEyeWinCoords;
	private double[] targetEyeWinSizes;
	private NoisyMStickPngPsychometricTrialData trialData;
	double[] noiseChance;
	NAFCAllenMStickSpecs mStickSpecs = new NAFCAllenMStickSpecs();



	public void writeStimObjId() {
		DistancedDistractorsUtil ddUtil = new DistancedDistractorsUtil(numChoices, trialGenData.getChoiceDistanceLims().getDistanceLowerLim(), trialGenData.choiceDistanceLims.getDistanceUpperLim(), 0, 0);
		Coordinates2D matchCoords = ddUtil.getMatchCoords();
		List<Coordinates2D> distractorCoords = ddUtil.getDistractorCoordsAsList();
		writeSampleSpec();
		writeMatchSpec(matchCoords);
		writeDistractorSpecs(distractorCoords);
	}

	private void writeSampleSpec() {
		SampleSpecWriter sampleSpecWriter = new SampleSpecWriter(
				trialGenData.getSampleDistanceLims(),
				pngPaths.getSamplePath(), noiseMapPath,
				trialGenData.getSampleScale());

		sampleSpecWriter.buildSpec();
		NoisyPngSpec sampleSpec = sampleSpecWriter.getSpec();

		MStickStimObjData sampleMStickObjData = new MStickStimObjData("Sample", mStickSpecs.getSampleMStickSpec());
		dbUtil.writeStimObjData(stimObjIds.getSampleId(), sampleSpec.toXml(), sampleMStickObjData.toXml());
	}

	private void writeMatchSpec(Coordinates2D matchCoords) {

		NoisyPngSpecWriter matchSpecWriter = NoisyPngSpecWriter.createWithoutNoiseMap(
				matchCoords,
				pngPaths.getMatchPath(),
				trialGenData.getSampleScale());
		matchSpecWriter.buildSpec();
		NoisyPngSpec matchSpec = matchSpecWriter.getSpec();

		MStickStimObjData matchMStickObjData = new MStickStimObjData("Match", mStickSpecs.getMatchMStickSpec());
		dbUtil.writeStimObjData(stimObjIds.getMatchId(), matchSpec.toXml(), matchMStickObjData.toXml());
	}

	private void writeDistractorSpecs(List<Coordinates2D> distractorCoords) {
		int indx=0;
		for(Coordinates2D coord:distractorCoords) {
			NoisyPngSpecWriter distractorSpecWriter = NoisyPngSpecWriter.createWithoutNoiseMap(
					coord, pngPaths.getDistractorsPaths().get(indx),trialGenData.getSampleScale());
			distractorSpecWriter.buildSpec();
			NoisyPngSpec distractorSpec = distractorSpecWriter.getSpec();
			MStickStimObjData distractorMStickObjData = new MStickStimObjData("Distractor", mStickSpecs.getMatchMStickSpec());
			dbUtil.writeStimObjData(stimObjIds.getPsychometricDistractorsIds().get(indx), distractorSpec.toXml(), distractorMStickObjData.toXml());
			indx++;
		}
	}

	private class SampleSpecWriter extends NoisyPngSpecWriter {
		DistanceLims distance;
		public SampleSpecWriter(DistanceLims distance, String pngPath, String noiseMapPath,
				double  pngDimension) {
			this.pngPath = pngPath;
			this.noiseMapPath = noiseMapPath;
			this.pngDimensions = new ImageDimensions(pngDimension, pngDimension);
			this.distance = distance;
		}

		@Override
		protected void setCoords() {
			Coordinates2D coords = randomCoordsWithinRadii(distance.getDistanceLowerLim(), distance.getDistanceUpperLim());
			spec.setxCenter(coords.getX());
			spec.setyCenter(coords.getY());
		}
	}


}

