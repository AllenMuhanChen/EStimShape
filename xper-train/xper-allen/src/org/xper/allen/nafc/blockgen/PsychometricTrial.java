package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.nafc.vo.NoiseData;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.drawing.Coordinates2D;

/**
 * private class to write a PsychometricTrial to the database. 
 * 
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
	AllenMatchStick sampleObj;

	//fields that are written to the db 
		//stimObjData
	Long sampleId;
	String samplePngPath;
	String noiseMapPath;
	List<String> noiseMapLabels;
	AllenMStickSpec sampleMStickSpec;
	String matchPngPath;
	Long matchId;
	AllenMStickSpec matchMStickSpec;
	List<String> distractorsPngPaths = new LinkedList<String>();
	List<Long> distractorsIds = new LinkedList<Long>();
	List<AllenMStickSpec> distractorsMStickSpecs = new LinkedList<AllenMStickSpec>();
		//stimSpec
	Long taskId;
	Coordinates2D sampleCoords;
	Coordinates2D matchCoords;
	ArrayList<Coordinates2D> distractorsCoords;


	/**
	 * Called before db writing to assign necessary parameters. (order doesn't matter)
	 * @param setId
	 * @param stimId
	 * @param stimIds
	 * @param numPsychometricDistractors
	 * @param noiseChance
	 */
	public void prepareStimObjData(long setId, int stimId, List<Integer> stimIds, int numPsychometricDistractors,double[] noiseChance) {
		assignPsychometricStimuli(setId, stimId, stimIds, numPsychometricDistractors);
		loadMSticks();
		assignParamsForNoiseMapGen(noiseChance);
	}

	/**
	 * To be called when writing trial to the db. (order matters: only call this when the necessary
	 * shuffling and ordering has been done, since this assigns the id, ids need to be in descending order in the database.
	 * )
	 */
	@Override
	public void write() {
		assignDbIds();
		String generatorNoiseMapPath = generateNoiseMap();
		noiseMapPath = gen.convertNoiseMapPathToExperiment(generatorNoiseMapPath);
		//TODO: RAND DISTRACTORS
	}
	
	private String generateNoiseMap() {
		List<String> noiseMapLabels = new LinkedList<String>();
		noiseMapLabels.add(Long.toString(sampleSetId));
		noiseMapLabels.add(Integer.toString(sampleStimId));
		return gen.pngMaker.createAndSaveNoiseMapFromObj(sampleObj, sampleId, noiseMapLabels);
	}

	/**
	 * Assigns sample, match and psychometric distractors a set and stim id to link to specific .png and assigns
	 * the paths to those pngs in the experiment machine.  
	 * @param setId
	 * @param stimId
	 * @param stimIds
	 * @param numPsychometricDistractors
	 */
	private void assignPsychometricStimuli(long setId, int stimId, List<Integer> stimIds, int numPsychometricDistractors) {
		assignPsychometricIds(setId, stimId, stimIds, numPsychometricDistractors);
		assignPsychometricPaths(setId, stimId);
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

	private void assignPsychometricPaths(long setId, int stimId) {
		samplePngPath = gen.convertPathToExperiment(gen.generatorPngPath + "/" + setId + "_" + stimId + ".png");
		matchPngPath = samplePngPath;
		for (int remainingStimId:distractorsStimIds) {
			int index = distractorsStimIds.indexOf(remainingStimId);
			distractorsPngPaths.add(gen.convertPathToExperiment(gen.generatorPngPath + "/" + setId + "_" + remainingStimId + ".png"));
		}
	}
	
	/**
	 * Loads the MStick objs from specs of psychometric stimuli. 
	 */
	private void loadMSticks() {
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
	private void assignParamsForNoiseMapGen(double[] noiseChance) {
		noiseData = new NoiseData(NoiseType.PRE_JUNC, NoisyMStickPngPsychometricBlockGen.noiseNormalizedPosition_PRE_JUNC, noiseChance);
	}

	/**
	 * assigns sample, match and distractor Ids that will be written to the DB. sampleId is required
	 * for generating noisemaps!
	 */
	private void assignDbIds() {
		sampleId = gen.globalTimeUtil.currentTimeMicros();
		taskId = sampleId;
		matchId = sampleId+1;
		for (int j=0; j<numPsychometricDistractors+numRandDistractors;j++) {
			distractorsIds.add(matchId + 1 + j);
		}
	}

	private AllenMatchStick fetchSample() {
		String path = specPath + "/" + sampleSetId + "_" + sampleStimId + "_spec.xml";
		AllenMatchStick ams = new AllenMatchStick();
		this.gen.setProperties(ams);
		ams.genMatchStickFromFile(path);
		return ams;
	}

	private AllenMatchStick fetchMatch() {
		String path = specPath + "/" + matchSetId + "_" + matchStimId + "_spec.xml";
		AllenMatchStick ams = new AllenMatchStick();
		this.gen.setProperties(ams);
		ams.genMatchStickFromFile(path);
		return ams;
	}

	private List<AllenMatchStick> fetchDistractors(){
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






}