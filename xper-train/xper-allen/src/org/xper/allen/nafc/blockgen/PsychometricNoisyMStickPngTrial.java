package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.blockgen.NAFCTrial.DistancedDistractorsUtil;
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
public class PsychometricNoisyMStickPngTrial extends NAFCTrial{
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
	List<AllenMatchStick> objs_randDistractor = new ArrayList<AllenMatchStick>();

	//Parameter Fields
	NoisyMStickPngPsychometricTrialGenData trialGenData;
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
	List<Long> psychometricDistractorIds = new LinkedList<Long>();
	List<Long> randDistractorIds = new LinkedList<>();
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
	public PsychometricNoisyMStickPngTrial(AbstractPsychometricNoiseMapGenerator noisyMStickPngPsychometricBlockGen,
			int numPsychometricDistractors, int numRandDistractors) {
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
	public void prepareWrite(long setId, int stimId, List<Integer> stimIds, double[] noiseChance, NoisyMStickPngPsychometricTrialGenData trialGenData) {
		assignPsychometricStimuli(setId, stimId, stimIds);
		loadMSticks();
		assignParamsForNoiseMapGen(noiseChance);
		assignGenParams(trialGenData);
	}

	/**
	 * To be called when writing trial to the db. (order matters: only call this when the necessary
	 * shuffling and ordering has been done because this assigns the id. ids need to be in descending/chronological order in the database.
	 * to be properly loaded into xper. 
	 * @return the taskId of this particular trial. 
	 */
	@Override
	public Long write() {
		assignDbIds();
		prepareNoiseMap(); //noisemap needs proper ID. 
		genRandDistractors();
		writeStimObjId();
		writeStimSpec();
		return taskId;
	}

	private void assignGenParams(NoisyMStickPngPsychometricTrialGenData trialGenData) {
		this.trialGenData = trialGenData;
		sampleDistanceLowerLim = trialGenData.getSampleDistanceLowerLim();
		sampleDistanceUpperLim = trialGenData.getSampleDistanceUpperLim();
		choiceDistanceLowerLim = trialGenData.getChoiceDistanceLowerLim();
		choiceDistanceUpperLim = trialGenData.getChoiceDistanceUpperLim();
		sampleScale = trialGenData.getSampleScale();
		eyeWinSize = trialGenData.getEyeWinSize();
	}
	
	private void prepareNoiseMap() {
		String generatorNoiseMapPath = generateNoiseMap();
		noiseMapPath = gen.convertNoiseMapPathToExperiment(generatorNoiseMapPath);
	}

	private void genRandDistractors() {
		genRandDistractors_obj();
		drawRandDistractors();
		
	}

	private void genRandDistractors_obj() {
		System.out.println("Trying to Generate Rand Distractor");
		objs_randDistractor = new ArrayList<>();
		boolean tryagain = true;
		while(tryagain) {
			objs_randDistractor = new ArrayList<>();
			for(int i=0; i<numRandDistractors; i++) {
				objs_randDistractor.add(new AllenMatchStick());
			}
			boolean randDistractorsSuccess = false;
			Boolean[] randDistractorSuccess = new Boolean[numRandDistractors];
			for(int b=0; b<randDistractorSuccess.length; b++) randDistractorSuccess[b]=false;
			for(int j=0; j<numRandDistractors; j++) {
				try {
					gen.setProperties(objs_randDistractor.get(j));
					objs_randDistractor.get(j).genMatchStickRand();
					randDistractorSuccess[j] = true;
				} catch(Exception e) {
					e.printStackTrace();
					randDistractorSuccess[j] = false;
				}
				if(!randDistractorSuccess[j]) {
					objs_randDistractor.set(j, new AllenMatchStick());
				}
			}
			randDistractorsSuccess = !Arrays.asList(randDistractorSuccess).contains(false);

			if(randDistractorsSuccess) {
				tryagain = false;
			}
		}
	}

	private void drawRandDistractors() {
		List<String> sampleLabels = Arrays.asList(new String[] {"sample"});
		int indx=0;
		for (AllenMatchStick obj: objs_randDistractor) {
			String path = gen.pngMaker.createAndSavePNGFromObj(obj, randDistractorIds.get(indx), sampleLabels);
			distractorsPngPaths.add(path);
		}
	}

	private void writeStimObjId() {
		//COORDS
		sampleCoords = randomWithinRadius(sampleDistanceLowerLim, sampleDistanceUpperLim);
		DistancedDistractorsUtil ddUtil = new DistancedDistractorsUtil(numChoices, choiceDistanceLowerLim, choiceDistanceUpperLim, 0, 0);
		distractorsCoords = (ArrayList<Coordinates2D>) ddUtil.getDistractorCoordsAsList();
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
		sampleObj.setNoiseParameters(noiseData);
	}

	/**
	 * assigns sample, match and distractor Ids that will be written to the DB. sampleId is required
	 * for generating noisemaps!
	 */
	private void assignDbIds() {
		sampleId = gen.globalTimeUtil.currentTimeMicros();
		taskId = sampleId;
		matchId = sampleId+1;
		long prevId = matchId;
		for (int j=0; j<numPsychometricDistractors;j++) {
			psychometricDistractorIds.add(prevId+1);
			distractorsIds.add(prevId+1);
			prevId++;
		}
		for (int j=0; j<numRandDistractors;j++) {
			randDistractorIds.add(prevId+1);
			distractorsIds.add(prevId+1);
			prevId++;
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

	public AbstractPsychometricNoiseMapGenerator getGen() {
		return gen;
	}

	public void setGen(AbstractPsychometricNoiseMapGenerator gen) {
		this.gen = gen;
	}

	public AllenDbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(AllenDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public String getSpecPath() {
		return specPath;
	}

	public void setSpecPath(String specPath) {
		this.specPath = specPath;
	}

	public long getSampleSetId() {
		return sampleSetId;
	}

	public void setSampleSetId(long sampleSetId) {
		this.sampleSetId = sampleSetId;
	}

	public int getSampleStimId() {
		return sampleStimId;
	}

	public void setSampleStimId(int sampleStimId) {
		this.sampleStimId = sampleStimId;
	}

	public NoiseData getNoiseData() {
		return noiseData;
	}

	public void setNoiseData(NoiseData noiseData) {
		this.noiseData = noiseData;
	}

	public long getMatchSetId() {
		return matchSetId;
	}

	public void setMatchSetId(long matchSetId) {
		this.matchSetId = matchSetId;
	}

	public int getMatchStimId() {
		return matchStimId;
	}

	public void setMatchStimId(int matchStimId) {
		this.matchStimId = matchStimId;
	}

	public long getDistractorsSetId() {
		return distractorsSetId;
	}

	public void setDistractorsSetId(long distractorsSetId) {
		this.distractorsSetId = distractorsSetId;
	}

	public List<Integer> getDistractorsStimIds() {
		return distractorsStimIds;
	}

	public void setDistractorsStimIds(List<Integer> distractorsStimIds) {
		this.distractorsStimIds = distractorsStimIds;
	}

	public int getNumPsychometricDistractors() {
		return numPsychometricDistractors;
	}

	public void setNumPsychometricDistractors(int numPsychometricDistractors) {
		this.numPsychometricDistractors = numPsychometricDistractors;
	}

	public int getNumRandDistractors() {
		return numRandDistractors;
	}

	public void setNumRandDistractors(int numRandDistractors) {
		this.numRandDistractors = numRandDistractors;
	}

	public int getNumDistractors() {
		return numDistractors;
	}

	public void setNumDistractors(int numDistractors) {
		this.numDistractors = numDistractors;
	}

	public int getNumChoices() {
		return numChoices;
	}

	public void setNumChoices(int numChoices) {
		this.numChoices = numChoices;
	}

	public AllenMatchStick getSampleObj() {
		return sampleObj;
	}

	public void setSampleObj(AllenMatchStick sampleObj) {
		this.sampleObj = sampleObj;
	}

	public double getSampleDistanceLowerLim() {
		return sampleDistanceLowerLim;
	}

	public void setSampleDistanceLowerLim(double sampleDistanceLowerLim) {
		this.sampleDistanceLowerLim = sampleDistanceLowerLim;
	}

	public double getSampleDistanceUpperLim() {
		return sampleDistanceUpperLim;
	}

	public void setSampleDistanceUpperLim(double sampleDistanceUpperLim) {
		this.sampleDistanceUpperLim = sampleDistanceUpperLim;
	}

	public double getChoiceDistanceLowerLim() {
		return choiceDistanceLowerLim;
	}

	public void setChoiceDistanceLowerLim(double choiceDistanceLowerLim) {
		this.choiceDistanceLowerLim = choiceDistanceLowerLim;
	}

	public double getChoiceDistanceUpperLim() {
		return choiceDistanceUpperLim;
	}

	public void setChoiceDistanceUpperLim(double choiceDistanceUpperLim) {
		this.choiceDistanceUpperLim = choiceDistanceUpperLim;
	}

	public double getSampleScale() {
		return sampleScale;
	}

	public void setSampleScale(double sampleScale) {
		this.sampleScale = sampleScale;
	}

	public double getEyeWinSize() {
		return eyeWinSize;
	}

	public void setEyeWinSize(double eyeWinSize) {
		this.eyeWinSize = eyeWinSize;
	}

	public Long getSampleId() {
		return sampleId;
	}

	public void setSampleId(Long sampleId) {
		this.sampleId = sampleId;
	}

	public String getSamplePngPath() {
		return samplePngPath;
	}

	public void setSamplePngPath(String samplePngPath) {
		this.samplePngPath = samplePngPath;
	}

	public String getNoiseMapPath() {
		return noiseMapPath;
	}

	public void setNoiseMapPath(String noiseMapPath) {
		this.noiseMapPath = noiseMapPath;
	}

	public List<String> getNoiseMapLabels() {
		return noiseMapLabels;
	}

	public void setNoiseMapLabels(List<String> noiseMapLabels) {
		this.noiseMapLabels = noiseMapLabels;
	}

	public AllenMStickSpec getSampleMStickSpec() {
		return sampleMStickSpec;
	}

	public void setSampleMStickSpec(AllenMStickSpec sampleMStickSpec) {
		this.sampleMStickSpec = sampleMStickSpec;
	}

	public String getMatchPngPath() {
		return matchPngPath;
	}

	public void setMatchPngPath(String matchPngPath) {
		this.matchPngPath = matchPngPath;
	}

	public Long getMatchId() {
		return matchId;
	}

	public void setMatchId(Long matchId) {
		this.matchId = matchId;
	}

	public AllenMStickSpec getMatchMStickSpec() {
		return matchMStickSpec;
	}

	public void setMatchMStickSpec(AllenMStickSpec matchMStickSpec) {
		this.matchMStickSpec = matchMStickSpec;
	}

	public List<String> getDistractorsPngPaths() {
		return distractorsPngPaths;
	}

	public void setDistractorsPngPaths(List<String> distractorsPngPaths) {
		this.distractorsPngPaths = distractorsPngPaths;
	}

	public List<Long> getDistractorsIds() {
		return distractorsIds;
	}

	public void setDistractorsIds(List<Long> distractorsIds) {
		this.distractorsIds = distractorsIds;
	}

	public List<AllenMStickSpec> getDistractorsMStickSpecs() {
		return distractorsMStickSpecs;
	}

	public void setDistractorsMStickSpecs(List<AllenMStickSpec> distractorsMStickSpecs) {
		this.distractorsMStickSpecs = distractorsMStickSpecs;
	}

	public Coordinates2D getSampleCoords() {
		return sampleCoords;
	}

	public void setSampleCoords(Coordinates2D sampleCoords) {
		this.sampleCoords = sampleCoords;
	}

	public Coordinates2D getMatchCoords() {
		return matchCoords;
	}

	public void setMatchCoords(Coordinates2D matchCoords) {
		this.matchCoords = matchCoords;
	}

	public ArrayList<Coordinates2D> getDistractorsCoords() {
		return distractorsCoords;
	}

	public void setDistractorsCoords(ArrayList<Coordinates2D> distractorsCoords) {
		this.distractorsCoords = distractorsCoords;
	}

	public long[] geteStimObjData() {
		return eStimObjData;
	}

	public void seteStimObjData(long[] eStimObjData) {
		this.eStimObjData = eStimObjData;
	}

	public RewardPolicy getRewardPolicy() {
		return rewardPolicy;
	}

	public void setRewardPolicy(RewardPolicy rewardPolicy) {
		this.rewardPolicy = rewardPolicy;
	}

	public int[] getRewardList() {
		return rewardList;
	}

	public void setRewardList(int[] rewardList) {
		this.rewardList = rewardList;
	}

	public List<Coordinates2D> getTargetEyeWinCoords() {
		return targetEyeWinCoords;
	}

	public void setTargetEyeWinCoords(List<Coordinates2D> targetEyeWinCoords) {
		this.targetEyeWinCoords = targetEyeWinCoords;
	}

	public double[] getTargetEyeWinSizes() {
		return targetEyeWinSizes;
	}

	public void setTargetEyeWinSizes(double[] targetEyeWinSizes) {
		this.targetEyeWinSizes = targetEyeWinSizes;
	}

	public NoisyMStickPngPsychometricTrialData getTrialData() {
		return trialData;
	}

	public void setTrialData(NoisyMStickPngPsychometricTrialData trialData) {
		this.trialData = trialData;
	}

	public List<AllenMatchStick> getObjs_randDistractor() {
		return objs_randDistractor;
	}

	public void setObjs_randDistractor(List<AllenMatchStick> objs_randDistractor) {
		this.objs_randDistractor = objs_randDistractor;
	}






}