package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.blockgen.AbstractTrialGenerator.DistancedDistractorsUtil;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.nafc.vo.MStickStimObjData;
import org.xper.allen.nafc.vo.NoiseData;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;

/**
 * private class to write a PsychometricTrial to the database. 
 * 
 * @author r2_allen
 *
 */
class PsychometricTrial implements Trial{
	/**
	 * 
	 */
	private AbstractPsychometricNoiseMapGenerator gen;
	private AllenDbUtil dbUtil;

	
	//Fields to help with calculations and not directly written to db
	String specPath;
	long sampleSetId;
	int sampleStimId;
	NoiseData noiseData;
	long matchSetId;
	int matchStimId;
	long distractorsSetId;
	List<Integer> distractorsStimIds;
	int numPsychometricDistractors;
	int numRandDistractors;
	int numDistractors;
	int numChoices;
	AllenMatchStick sampleObj;
	
	//Parameter Fields
	double sampleDistanceLowerLim;
	double sampleDistanceUpperLim; 
	double choiceDistanceLowerLim;
	double choiceDistanceUpperLim;
	double sampleScale;
	double eyeWinSize;

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
	private long[] eStimObjData;
	private RewardPolicy rewardPolicy;
	private int[] rewardList;
	private List<Coordinates2D> targetEyeWinCoords;
	private double[] targetEyeWinSizes;
	private NoisyMStickPngPsychometricTrialData trialData;


	/**
	 * @param noisyMStickPngPsychometricBlockGen
	 * @param numPsychometricDistractors TODO
	 * @param numRandDistractors TODO
	 */
	PsychometricTrial(AbstractPsychometricNoiseMapGenerator noisyMStickPngPsychometricBlockGen, int numPsychometricDistractors, int numRandDistractors) {
		this.gen = noisyMStickPngPsychometricBlockGen;
		dbUtil = gen.getDbUtil();
		specPath = gen.generatorSpecPath;
		this.numPsychometricDistractors = numPsychometricDistractors;
		this.numRandDistractors = numRandDistractors;
		this.numDistractors = numPsychometricDistractors + numRandDistractors;
		this.numChoices = numDistractors+1;
	}

	/**
	 * Called before db writing to assign necessary parameters. (order doesn't matter)
	 * @param setId
	 * @param stimId
	 * @param stimIds
	 * @param noiseChance
	 */
	public void prepareWrite(long setId, int stimId, List<Integer> stimIds, double[] noiseChance) {
		assignPsychometricStimuli(setId, stimId, stimIds);
		loadMSticks();
		assignParamsForNoiseMapGen(noiseChance);
	}

	/**
	 * To be called when writing trial to the db. (order matters: only call this when the necessary
	 * shuffling and ordering has been done, since this assigns the id, ids need to be in descending/chronological order in the database.
	 * to be properly loaded into xper. 
	 * @return the taskId of this particular trial. 
	 */
	@Override
	public Long write() {
		assignDbIds();
		prepareNoiseMap(); //noisemap needs proper ID. 
		//TODO: RAND DISTRACTORS
		writeStimObjId();
		writeStimSpec();
		return taskId;
	}
	
	private void prepareNoiseMap() {
		String generatorNoiseMapPath = generateNoiseMap();
		noiseMapPath = gen.convertNoiseMapPathToExperiment(generatorNoiseMapPath);
	}
	
	private void writeStimObjId() {
		//COORDS
		sampleCoords = AbstractPsychometricNoiseMapGenerator.randomWithinRadius(sampleDistanceLowerLim, sampleDistanceUpperLim);
		DistancedDistractorsUtil ddUtil = gen.new DistancedDistractorsUtil(numChoices, choiceDistanceLowerLim, choiceDistanceUpperLim, 0, 0);
		ArrayList<Coordinates2D> distractorsCoords = (ArrayList<Coordinates2D>) ddUtil.getDistractorCoordsAsList();
		matchCoords = ddUtil.getMatchCoords();
		
		//SAMPLE SPEC
		NoisyPngSpec sampleSpec = new NoisyPngSpec();
		sampleSpec.setPath(samplePngPath);
		sampleSpec.setNoiseMapPath(noiseMapPath);
		sampleSpec.setxCenter(sampleCoords.getX());
		sampleSpec.setyCenter(sampleCoords.getY());
		ImageDimensions sampleDimensions = new ImageDimensions(sampleScale, sampleScale);
		sampleSpec.setImageDimensions(sampleDimensions);
		MStickStimObjData sampleMStickObjData = new MStickStimObjData("Sample", sampleMStickSpec);
		dbUtil.writeStimObjData(sampleId, sampleSpec.toXml(), sampleMStickObjData.toXml());
		
		//MATCH SPEC
		NoisyPngSpec matchSpec = new NoisyPngSpec();
		matchSpec.setPath(matchPngPath);
		matchSpec.setxCenter(matchCoords.getX());
		matchSpec.setyCenter(matchCoords.getY());
		ImageDimensions matchDimensiosn = new ImageDimensions(sampleScale, sampleScale);
		matchSpec.setImageDimensions(matchDimensiosn);
		MStickStimObjData matchMStickObjData = new MStickStimObjData("Match", matchMStickSpec);
		dbUtil.writeStimObjData(matchId, matchSpec.toXml(), matchMStickObjData.toXml());

		//DISTRACTORS SPECS
		for (Long distractorId:distractorsIds) {
			int indx = distractorsIds.indexOf(distractorId);
			NoisyPngSpec distractorSpec = new NoisyPngSpec();
			distractorSpec.setPath(distractorsPngPaths.get(indx));
			distractorSpec.setxCenter(distractorsCoords.get(indx).getX());
			distractorSpec.setyCenter(distractorsCoords.get(indx).getY());
			ImageDimensions distractorDimensions = new ImageDimensions(sampleScale, sampleScale);
			distractorSpec.setImageDimensions(distractorDimensions);
			MStickStimObjData distractorMStickObjData = new MStickStimObjData("Distractor", matchMStickSpec);
			dbUtil.writeStimObjData(distractorsIds.get(indx), distractorSpec.toXml(), distractorMStickObjData.toXml());
		}
	}
	
	private void writeStimSpec() {
		targetEyeWinCoords = new LinkedList<Coordinates2D>();
		targetEyeWinCoords.add(matchCoords);
		targetEyeWinCoords.addAll(distractorsCoords);
		targetEyeWinSizes = new double[numChoices];
		for(int j=0; j < numChoices; j++) {
			targetEyeWinSizes[j] = eyeWinSize;
		}
		writeEStimObjData();
		long[] choiceIds = new long[numChoices];
		choiceIds[0] = matchId;
		for (int distractorIdIndx=0; distractorIdIndx<distractorsIds.size(); distractorIdIndx++) {
			choiceIds[distractorIdIndx+1] = distractorsIds.get(distractorIdIndx);
		}
		NAFCStimSpecSpec stimSpec = new NAFCStimSpecSpec(targetEyeWinCoords.toArray(new Coordinates2D[0]), targetEyeWinSizes, sampleId, choiceIds, eStimObjData, rewardPolicy, rewardList);
		writeTrialData();
		dbUtil.writeStimSpec(taskId, stimSpec.toXml(), trialData.toXml());
	}
	
	private void writeTrialData() {
		NoisyMStickPngPsychometricTrialGenData trialGenData = new NoisyMStickPngPsychometricTrialGenData(sampleDistanceLowerLim, sampleDistanceUpperLim, choiceDistanceLowerLim, choiceDistanceUpperLim, sampleScale, eyeWinSize);
		trialData = new NoisyMStickPngPsychometricTrialData(noiseData, trialGenData);
	}
	
	private void writeEStimObjData() {
		eStimObjData = new long[] {1};
		rewardPolicy = RewardPolicy.LIST;
		rewardList = new int[] {0};
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
	 */
	private void assignPsychometricStimuli(long setId, int stimId, List<Integer> stimIds) {
		assignPsychometricIds(setId, stimId, stimIds);
		assignPsychometricPaths(setId, stimId);
	}

	/**
	 * Assigns sample, match and psychometric distractors a set and stim id to link it to a specific .png
	 * @param setId
	 * @param stimId
	 * @param stimIds
	 */
	private void assignPsychometricIds(long setId, int stimId, List<Integer> stimIds) {
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

	public Long getTaskId() {
		return taskId;
	}

	public void setTaskId(Long taskId) {
		this.taskId = taskId;
	}






}