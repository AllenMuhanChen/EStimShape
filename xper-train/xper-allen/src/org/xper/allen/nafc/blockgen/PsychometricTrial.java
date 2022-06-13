package org.xper.allen.nafc.blockgen;

import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.nafc.vo.NoiseData;
import org.xper.allen.nafc.vo.NoiseType;

/**
 * private class to write a PsychometricTrial to the database. 
 * @author r2_allen
 *
 */
class PsychometricTrial implements NAFCTrial{
	/**
	 * 
	 */
	private NoisyMStickPngPsychometricBlockGen gen;


	/**
	 * @param noisyMStickPngPsychometricBlockGen
	 */
	PsychometricTrial(NoisyMStickPngPsychometricBlockGen noisyMStickPngPsychometricBlockGen) {
		this.gen = noisyMStickPngPsychometricBlockGen;
	}

	//Fields to help with calculations and not directly written to db
	String specPath = gen.generatorSpecPath;
	long sampleSetId;
	int sampleStimId;
	NoiseData noiseData;

	long matchSetId;
	int matchStimId;

	long distractorsSetId;
	List<Integer> distractorsStimIds;

	int numPsychometricDistractors;
	int numRandDistractors;
	//fields that are written to the db 
	Long sampleId;
	String samplePngPath;
	String noiseMapPath;
	AllenMStickSpec sampleMStickSpec;

	String matchPngPath;
	Long matchId;
	AllenMStickSpec matchMStickSpec;

	List<String> distractorsPngPaths = new LinkedList<String>();
	List<Long> distractorsIds = new LinkedList<Long>();
	List<AllenMStickSpec> distractorsMStickSpecs = new LinkedList<AllenMStickSpec>();
	
	AllenMatchStick sampleObj;
	/**
	 * Assigns sample, match and psychometric distractors a set and stim id to link to specific .png and assigns
	 * the paths to those pngs in the experiment machine.  
	 * @param setId
	 * @param stimId
	 * @param stimIds
	 * @param numPsychometricDistractors
	 */
	public void assignPsychometricStimuli(long setId, int stimId, List<Integer> stimIds, int numPsychometricDistractors) {
		assignPsychometricIds(setId, stimId, stimIds, numPsychometricDistractors);
		assignPaths(setId, stimId);
	}
	

	
	public void loadMSticks() {
//		sampleId = gen.globalTimeUtil.currentTimeMicros();
		sampleObj = fetchSample();
		sampleMStickSpec = new AllenMStickSpec();
		sampleMStickSpec.setMStickInfo(sampleObj);
		
//		sampleObj.setNoiseParameters(noiseData);
		
		matchMStickSpec = new AllenMStickSpec();
		matchMStickSpec.setMStickInfo(fetchMatch());
		
		for(AllenMatchStick distractorObj:fetchDistractors()) {
			AllenMStickSpec distractorMStickSpec = new AllenMStickSpec();
			distractorMStickSpec.setMStickInfo(distractorObj);
			distractorsMStickSpecs.add(distractorMStickSpec);
		}
	}
	
	/**
	 * Assign parameters required to generate a noise map from the sample
	 * @param setId
	 * @param stimId
	 */
	public void assignParamsForNoiseMapGen(double[] noiseChance) {
		
		this.noiseData = new NoiseData(NoiseType.PRE_JUNC, NoisyMStickPngPsychometricBlockGen.noiseNormalizedPosition_PRE_JUNC, noiseChance);
		 assignIds();
	}
	
	/**
	 * assigns sample, match and distractor Ids that will be written to the DB. sampleId is required
	 * for generating noisemaps!
	 */
	private void assignIds() {
		sampleId = gen.globalTimeUtil.currentTimeMicros();
		matchId = sampleId+1;
		for (int j=0; j<numPsychometricDistractors+numRandDistractors;j++) {
			distractorsIds.add(matchId + 1 + j);
		}
	}
	
	/**
	 * Assigns sample, match and psychometric distractors a set and stim id to link it to a specific .png
	 * @param setId
	 * @param stimId
	 * @param stimIds
	 * @param numPsychometricDistractors
	 */
	private void assignPsychometricIds(long setId, int stimId, List<Integer> stimIds, int numPsychometricDistractors) {
		this.numPsychometricDistractors = numPsychometricDistractors;
		
		sampleSetId = setId;
		sampleStimId = stimId;
		
		matchSetId = setId;
		matchStimId = stimId;
		
		distractorsSetId = setId;
		List<Integer> stimIdsRemaining = new LinkedList<>(stimIds);
		stimIdsRemaining.remove(stimIds.indexOf(stimId));
		Collections.shuffle(stimIdsRemaining);
		distractorsStimIds = stimIdsRemaining.subList(0, numPsychometricDistractors);		
	}
	
	private void assignPaths(long setId, int stimId) {
		samplePngPath = gen.convertPathToExperiment(gen.generatorPngPath + "/" + setId + "_" + stimId + ".png");
		matchPngPath = samplePngPath;
		for (int remainingStimId:distractorsStimIds) {
			int index = distractorsStimIds.indexOf(remainingStimId);
			distractorsPngPaths.add(gen.convertPathToExperiment(gen.generatorPngPath + "/" + setId + "_" + remainingStimId + ".png"));
		}
	}
	


	public AllenMatchStick fetchSample() {
		String path = specPath + "/" + sampleSetId + "_" + sampleStimId + "_spec.xml";
		AllenMatchStick ams = new AllenMatchStick();
		this.gen.setProperties(ams);
		ams.genMatchStickFromFile(path);
		return ams;
	}

	public AllenMatchStick fetchMatch() {
		String path = specPath + "/" + matchSetId + "_" + matchStimId + "_spec.xml";
		AllenMatchStick ams = new AllenMatchStick();
		this.gen.setProperties(ams);
		ams.genMatchStickFromFile(path);
		return ams;
	}

	public List<AllenMatchStick> fetchDistractors(){
		List<AllenMatchStick> amss = new LinkedList<AllenMatchStick>();

		for (Integer stimId : distractorsStimIds) {
			String path = specPath + "/" + distractorsSetId + "_" + stimId + "_spec.xml";
			AllenMatchStick ams = new AllenMatchStick();
			this.gen.setProperties(ams);
			ams.genMatchStickFromFile(path);
			amss.add(ams);
		}

		return amss;
	}



	@Override
	public void write() {
		// TODO Auto-generated method stub
		
	}


}