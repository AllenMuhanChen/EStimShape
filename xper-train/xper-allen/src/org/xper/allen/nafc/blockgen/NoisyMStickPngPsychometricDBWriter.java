package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.List;

import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.blockgen.NAFCTrialWriter.DistancedDistractorsUtil;
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
public class NoisyMStickPngPsychometricDBWriter extends NAFCTrialWriter{
	
	NoisyMStickPngPsychometricTrialGenData trialGenData;
	int numChoices;
	NAFCPngPaths pngPaths;
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

	private void loadMStickSpecs() {
		
	}
	
	private void writeStimObjId() {
		//COORDS
		sampleCoords = randomWithinRadius(trialGenData.sampleDistanceLowerLim, trialGenData.sampleDistanceUpperLim);
		DistancedDistractorsUtil ddUtil = new DistancedDistractorsUtil(numChoices, trialGenData.choiceDistanceLowerLim, trialGenData.choiceDistanceUpperLim, 0, 0);
		distractorsCoords = (ArrayList<Coordinates2D>) ddUtil.getDistractorCoordsAsList();
		matchCoords = ddUtil.getMatchCoords();

		//SAMPLE SPEC
		NoisyPngSpec sampleSpec = new NoisyPngSpec();
		sampleSpec.setPath(pngPaths.samplePngPath);
		sampleSpec.setNoiseMapPath(noiseMapPath);
		sampleSpec.setxCenter(sampleCoords.getX());
		sampleSpec.setyCenter(sampleCoords.getY());
		ImageDimensions sampleDimensions = new ImageDimensions(trialGenData.sampleScale, trialGenData.sampleScale);
		sampleSpec.setImageDimensions(sampleDimensions);
		MStickStimObjData sampleMStickObjData = new MStickStimObjData("Sample", sampleMStickSpec);
		dbUtil.writeStimObjData(stimObjIds.getSampleId(), sampleSpec.toXml(), sampleMStickObjData.toXml());

		//MATCH SPEC
		NoisyPngSpec matchSpec = new NoisyPngSpec();
		matchSpec.setPath(pngPaths.matchPngPath);
		matchSpec.setxCenter(matchCoords.getX());
		matchSpec.setyCenter(matchCoords.getY());
		ImageDimensions matchDimensiosn = new ImageDimensions(trialGenData.sampleScale, trialGenData.sampleScale);
		matchSpec.setImageDimensions(matchDimensiosn);
		MStickStimObjData matchMStickObjData = new MStickStimObjData("Match", matchMStickSpec);
		dbUtil.writeStimObjData(stimObjIds.getMatchId(), matchSpec.toXml(), matchMStickObjData.toXml());

		//DISTRACTORS SPECS
		int indx=0;
		for(String psychometricPngPath : pngPaths.getDistractorsPngPaths()) {
			NoisyPngSpec distractorSpec = new NoisyPngSpec();
			distractorSpec.setPath(pngPaths.distractorsPngPaths.get(indx));
			distractorSpec.setxCenter(distractorsCoords.get(indx).getX());
			distractorSpec.setyCenter(distractorsCoords.get(indx).getY());
			ImageDimensions distractorDimensions = new ImageDimensions(trialGenData.sampleScale, trialGenData.sampleScale);
			distractorSpec.setImageDimensions(distractorDimensions);
			MStickStimObjData distractorMStickObjData = new MStickStimObjData("Distractor", matchMStickSpec);
			dbUtil.writeStimObjData(stimObjIds.getPsychometricDistractorsIds().get(indx), distractorSpec.toXml(), distractorMStickObjData.toXml());
			indx++;
		}
		indx=0;
		//TODO: Add rand distractor logic here
		for (Long distractorId:stimObjIds.getRandDistractorsIds()) {
			NoisyPngSpec distractorSpec = new NoisyPngSpec();
			distractorSpec.setPath(pngPaths.getRandDistractorsPngPaths().get(indx));
			distractorSpec.setxCenter(distractorsCoords.get(indx).getX());
			distractorSpec.setyCenter(distractorsCoords.get(indx).getY());
			ImageDimensions distractorDimensions = new ImageDimensions(trialGenData.sampleScale, trialGenData.sampleScale);
			distractorSpec.setImageDimensions(distractorDimensions);
			MStickStimObjData distractorMStickObjData = new MStickStimObjData("Distractor", matchMStickSpec);
			dbUtil.writeStimObjData(stimObjIds.getRandDistractorsIds().get(indx), distractorSpec.toXml(), distractorMStickObjData.toXml());
			indx++;
		}
	}
}
