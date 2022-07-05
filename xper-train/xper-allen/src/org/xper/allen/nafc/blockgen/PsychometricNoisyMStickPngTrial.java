package org.xper.allen.nafc.blockgen;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.blockgen.NAFCTrialWriter.DistancedDistractorsUtil;
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
public class PsychometricNoisyMStickPngTrial extends NAFCTrialWriter implements Trial{
	
	
	/**
	 * 
	 */
	AbstractPsychometricNoiseMapGenerator gen;
	private AllenDbUtil dbUtil;



	NoiseData noiseData;

	int numChoices;
	AllenMatchStick sampleObj;
	

	//Parameter Fields
	NoisyMStickPngPsychometricTrialGenData trialGenData;


	String noiseMapPath;
	List<String> noiseMapLabels;
	AllenMStickSpec sampleMStickSpec;

	AllenMStickSpec matchMStickSpec;

	
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
	double[] noiseChance;
	
	//REFRACTOR
	PsychometricPathAssigner psychometricPathAssigner;
	NumberOfDistractors numDistractors;
	StimObjIdAssignerForPsychometricAndRand stimObjIdAssigner;

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
		
		this.gen = noisyMStickPngPsychometricBlockGen;
		this.numDistractors = numDistractors;
		this.noiseChance = noiseChance;
		this.trialGenData = trialGenData;
		
		dbUtil = gen.getDbUtil();

		
		this.numChoices = numDistractors.numTotal+1;
		//AC refractor
		PngBasePaths basePaths = new PngBasePaths(gen.generatorPngPath, gen.experimentPngPath, gen.generatorSpecPath);
		this.psychometricPathAssigner = new PsychometricPathAssigner(psychometricIds, numDistractors.numPsychometricDistractors, basePaths);
		this.stimObjIdAssigner = new StimObjIdAssignerForPsychometricAndRand(gen.getGlobalTimeUtil(), numDistractors);
		
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
		psychometricPathAssigner.assign();
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
		generateNoiseMap();
		generateRandDistractors();
		assignGenParams(trialGenData);
	 //noisemap needs proper ID. 
		
		writeStimObjId();
		writeStimSpec();
		return taskId;
	}

	private void assignStimObjIds() {
		stimObjIdAssigner.assignStimObjIds();
	}


	private void generateNoiseMap() {
		NoiseMapGenerator noiseMapGenerator = 
				new NoiseMapGenerator(psychometricPathAssigner.getSampleSpecPath(),
									  psychometricPathAssigner.psychometricIds,
									  gen,
									  noiseChance,
									  stimObjIdAssigner.getSampleId());
		noiseMapGenerator.generate();
		noiseMapPath = noiseMapGenerator.getNoiseMapPath();
	}
	
	List<String> randDistractorsPngPaths;
	List<AllenMatchStick> objs_randDistractors;
	private void generateRandDistractors() {
		RandDistractorGenerator randDistractorGenerator = new RandDistractorGenerator(numDistractors, gen, stimObjIdAssigner.getRandDistractorsIds(), psychometricPathAssigner.pngPaths.distractorsPngPaths);
		randDistractorGenerator.genRandDistractors();
		randDistractorsPngPaths = randDistractorGenerator.getRandDistractorsPngPaths();
		objs_randDistractors = randDistractorGenerator.getObjs_randDistractor();
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








	private AllenMatchStick fetchSample() {
		String path = psychometricPathAssigner.getSpecPath();
		AllenMatchStick ams = new AllenMatchStick();
		this.gen.setProperties(ams);
		ams.genMatchStickFromFile(path);
		return ams;
	}

	private AllenMatchStick fetchMatch() {
		String path = psychometricPathAssigner.getMatchSpecPath();
		AllenMatchStick ams = new AllenMatchStick();
		this.gen.setProperties(ams);
		ams.genMatchStickFromFile(path);
		return ams;
	}

	private List<AllenMatchStick> fetchDistractors(){
		List<AllenMatchStick> amss = new LinkedList<AllenMatchStick>();
		List<String> paths = psychometricPathAssigner.getDistractorsSpecPaths();
		for (String path : paths) {
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

	public AllenMatchStick getSampleObj() {
		return sampleObj;
	}

	public void setSampleObj(AllenMatchStick sampleObj) {
		this.sampleObj = sampleObj;
	}

	public double getSampleDistanceUpperLim() {
		return trialGenData.sampleDistanceUpperLim;
	}

	public void setSampleDistanceUpperLim(double sampleDistanceUpperLim) {
		this.trialGenData.sampleDistanceUpperLim = sampleDistanceUpperLim;
	}

	public double getChoiceDistanceLowerLim() {
		return trialGenData.choiceDistanceLowerLim;
	}

	public void setChoiceDistanceLowerLim(double choiceDistanceLowerLim) {
		this.trialGenData.choiceDistanceLowerLim = choiceDistanceLowerLim;
	}

	public double getChoiceDistanceUpperLim() {
		return trialGenData.choiceDistanceUpperLim;
	}

	public void setChoiceDistanceUpperLim(double choiceDistanceUpperLim) {
		this.trialGenData.choiceDistanceUpperLim = choiceDistanceUpperLim;
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
		return sampleMStickSpec;
	}

	public void setSampleMStickSpec(AllenMStickSpec sampleMStickSpec) {
		this.sampleMStickSpec = sampleMStickSpec;
	}


	public AllenMStickSpec getMatchMStickSpec() {
		return matchMStickSpec;
	}

	public void setMatchMStickSpec(AllenMStickSpec matchMStickSpec) {
		this.matchMStickSpec = matchMStickSpec;
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







}