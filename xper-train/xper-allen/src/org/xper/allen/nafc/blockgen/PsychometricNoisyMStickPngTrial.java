package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.png.ImageDimensions;
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
public class PsychometricNoisyMStickPngTrial extends NAFCSpecWriter implements Trial{


	/**
	 * 
	 */
	AbstractPsychometricNoiseMapGenerator generator;
	private AllenDbUtil dbUtil;



	NoiseData noiseData;

	int numChoices;



	//Parameter Fields
	NoisyMStickPngPsychometricTrialGenData trialGenData;


	String noiseMapPath;
	List<String> noiseMapLabels;


	List<Long> psychometricDistractorIds = new LinkedList<Long>();
	List<Long> randDistractorIds = new LinkedList<>();

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
	double[] noiseChance;
	
	//REFRACTOR
	PsychometricIds psychometricIds;
	NumberOfDistractors numDistractors;
	
	NAFCPaths pngPaths;
	NAFCPaths specPaths;
	
	NAFCAllenMStickSpecs mStickSpecs = new NAFCAllenMStickSpecs();
	NAFCAllenMatchSticks matchSticks = new NAFCAllenMatchSticks();

	StimObjIdsForMixedPsychometricAndRand stimObjIds;
	/**
	 * @param noisyMStickPngPsychometricBlockGen
	 * @param numPsychometricDistractors TODO
	 * @param numRandDistractors TODO
	 */
	public PsychometricNoisyMStickPngTrial(
			AbstractPsychometricNoiseMapGenerator noisyMStickPngPsychometricBlockGen,
			NumberOfDistractors numDistractors, 
			PsychometricIds psychometricIds,
			double[] noiseChance,
			NoisyMStickPngPsychometricTrialGenData trialGenData) {

		this.generator = noisyMStickPngPsychometricBlockGen;
		this.numDistractors = numDistractors;
		this.psychometricIds = psychometricIds;
		this.noiseChance = noiseChance;
		this.trialGenData = trialGenData;

		dbUtil = generator.getDbUtil();
		this.numChoices = numDistractors.numTotal+1;
		//AC refractor
		
	}

	/**
	 * Called before db writing to assign necessary parameters. (order doesn't matter)
	 * @param setId
	 * @param stimId
	 * @param stimIds
	 * @param noiseChance
	 */
	@Override
	public void preWrite() {
		assignPsychometricPaths();
	}

	private void assignPsychometricPaths() {
		PngBasePaths basePaths = new PngBasePaths(generator.generatorPngPath, generator.experimentPngPath, generator.generatorSpecPath);
		PsychometricPathAssigner psychometricPathAssigner = PsychometricPathAssigner.createWithNewNAFCPngPathsObj(psychometricIds, numDistractors.numPsychometricDistractors, basePaths);
		psychometricPathAssigner.assign();
		pngPaths = psychometricPathAssigner.getPngPaths();
		specPaths = psychometricPathAssigner.getSpecPaths();
	}

	/**
	 * To be called when writing trial to the db. (order matters: only call this when the necessary
	 * shuffling and ordering has been done because this assigns the id. ids need to be in descending/chronological order in the database.
	 * to be properly loaded into xper. 
	 * @return the taskId of this particular trial. 
	 */
	@Override
	public Long write() {
		assignStimObjIds();
		loadMSticks();
		generateNoiseMap();
		generateRandDistractors();
		writeSpecs();
//		assignGenParams(trialGenData);
		//noisemap needs proper ID. 

//		writeStimObjId();
//		writeStimSpec();
		return taskId;
	}

	private void assignStimObjIds() {
		StimObjIdAssignerForPsychometricAndRand stimObjIdAssigner = new StimObjIdAssignerForPsychometricAndRand(generator.getGlobalTimeUtil(), numDistractors);
		stimObjIdAssigner.assignStimObjIds();
		stimObjIds = stimObjIdAssigner.getStimObjIds();
	}

	private void loadMSticks() {
		NAFCAllenMatchStickFetcher fetcher = new NAFCAllenMatchStickFetcher(generator, specPaths);
		mStickSpecs = fetcher.getmStickSpecs();
		matchSticks = fetcher.getMatchSticks();
	}

	
	private void generateNoiseMap() {
		NoiseMapGenerator noiseMapGenerator = 
				new NoiseMapGenerator(matchSticks.getSampleMStick(),
						psychometricIds,
						generator,
						noiseChance,
						stimObjIds.getSampleId());
		noiseMapGenerator.generate();
		noiseMapPath = noiseMapGenerator.getNoiseMapPath();
	}

	List<String> randDistractorsPngPaths;
	List<AllenMatchStick> objs_randDistractors;
	
	private void generateRandDistractors() {
		RandDistractorGenerator randDistractorGenerator = new RandDistractorGenerator(numDistractors, generator, stimObjIds.getRandDistractorsIds(), pngPaths.distractorsPaths);
		randDistractorGenerator.genRandDistractors();
		randDistractorsPngPaths = randDistractorGenerator.getRandDistractorsPngPaths();
		
		pngPaths.addToDistractors(randDistractorsPngPaths);
		objs_randDistractors = randDistractorGenerator.getObjs_randDistractor();
	}


	private void writeSpecs() {
		
	}
	
	private void writeStimSpec() {
		targetEyeWinCoords = new LinkedList<Coordinates2D>();
		targetEyeWinCoords.add(matchCoords);
		targetEyeWinCoords.addAll(distractorsCoords);
		targetEyeWinSizes = new double[numChoices];
		for(int j=0; j < numChoices; j++) {
			targetEyeWinSizes[j] = trialGenData.eyeWinSize;
		}
		writeEStimObjData();
		long[] choiceIds = new long[numChoices];
		choiceIds[0] = stimObjIdAssigner.getMatchId();
		for (int distractorIdIndx=0; distractorIdIndx<stimObjIdAssigner.getAllDistractorsIds().size(); distractorIdIndx++) {
			choiceIds[distractorIdIndx+1] = stimObjIdAssigner.getAllDistractorsIds().get(distractorIdIndx);
		}
		NAFCStimSpecSpec stimSpec = new NAFCStimSpecSpec(targetEyeWinCoords.toArray(new Coordinates2D[0]), targetEyeWinSizes, stimObjIdAssigner.getSampleId(), choiceIds, eStimObjData, rewardPolicy, rewardList);
		writeTrialData();
		dbUtil.writeStimSpec(taskId, stimSpec.toXml(), trialData.toXml());
	}

	private void writeTrialData() {
		trialData = new NoisyMStickPngPsychometricTrialData(noiseData, trialGenData);
	}

	private void writeEStimObjData() {
		eStimObjData = new long[] {1};
		rewardPolicy = RewardPolicy.LIST;
		rewardList = new int[] {0};
	}


	public Long getTaskId() {
		return taskId;
	}

	public void setTaskId(Long taskId) {
		this.taskId = taskId;
	}

	public AbstractPsychometricNoiseMapGenerator getGen() {
		return generator;
	}

	public void setGen(AbstractPsychometricNoiseMapGenerator gen) {
		this.generator = gen;
	}

	public AllenDbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(AllenDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}


	public NoiseData getNoiseData() {
		return noiseData;
	}

	public void setNoiseData(NoiseData noiseData) {
		this.noiseData = noiseData;
	}



	public int getNumChoices() {
		return numChoices;
	}

	public void setNumChoices(int numChoices) {
		this.numChoices = numChoices;
	}



	public double getSampleScale() {
		return trialGenData.sampleScale;
	}

	public void setSampleScale(double sampleScale) {
		this.trialGenData.sampleScale = sampleScale;
	}

	public double getEyeWinSize() {
		return trialGenData.eyeWinSize;
	}

	public void setEyeWinSize(double eyeWinSize) {
		this.trialGenData.eyeWinSize = eyeWinSize;
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
		return mStickSpecs.getSampleMStickSpec();
	}

	public void setSampleMStickSpec(AllenMStickSpec sampleMStickSpec) {
		this.mStickSpecs.setSampleMStickSpec(sampleMStickSpec);
	}


	public AllenMStickSpec getMatchMStickSpec() {
		return mStickSpecs.getMatchMStickSpec();
	}

	public void setMatchMStickSpec(AllenMStickSpec matchMStickSpec) {
		this.mStickSpecs.setMatchMStickSpec(matchMStickSpec);
	}

	public List<AllenMStickSpec> getDistractorsMStickSpecs() {
		return mStickSpecs.getDistractorsMStickSpecs();
	}

	public void setDistractorsMStickSpecs(List<AllenMStickSpec> distractorsMStickSpecs) {
		this.mStickSpecs.setDistractorsMStickSpecs(distractorsMStickSpecs);
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







}