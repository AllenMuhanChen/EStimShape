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
	AbstractPsychometricNoiseMapGenerator gen;
	private AllenDbUtil dbUtil;



	NoiseData noiseData;

	int numChoices;
	AllenMatchStick sampleObj;
	List<AllenMatchStick> objs_randDistractor = new ArrayList<AllenMatchStick>();

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

	//REFRACTOR
	PsychometricPathAssigner psychometricPathAssigner;
	NumberOfDistractors numDistractors;
	StimObjIdAssignerForPsychometricAndRand stimObjIds;
	
	/**
	 * @param noisyMStickPngPsychometricBlockGen
	 * @param numPsychometricDistractors TODO
	 * @param numRandDistractors TODO
	 */
	public PsychometricNoisyMStickPngTrial(AbstractPsychometricNoiseMapGenerator noisyMStickPngPsychometricBlockGen,
			NumberOfDistractors numDistractors, PsychometricIds psychometricIds) {
		this.gen = noisyMStickPngPsychometricBlockGen;
		this.numDistractors = numDistractors;
		
		dbUtil = gen.getDbUtil();

		
		this.numChoices = numDistractors.numTotal+1;
		//AC refractor
		PngBasePaths basePaths = new PngBasePaths(gen.generatorPngPath, gen.experimentPngPath, gen.generatorSpecPath);
		this.psychometricPathAssigner = new PsychometricPathAssigner(psychometricIds, numDistractors.numPsychometricDistractors, basePaths);
		this.stimObjIds = new StimObjIdAssignerForPsychometricAndRand(gen.getGlobalTimeUtil(), numDistractors);
	}

	/**
	 * Called before db writing to assign necessary parameters. (order doesn't matter)
	 * @param setId
	 * @param stimId
	 * @param stimIds
	 * @param noiseChance
	 */
	public void prepareWrite(double[] noiseChance, NoisyMStickPngPsychometricTrialGenData trialGenData) {
		psychometricPathAssigner.assign();
		loadMSticks(); //loadMSticks is only useful for generating noiseMap, so we can put them in same class
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
		stimObjIds.assignStimObjIds();
		prepareNoiseMap(); //noisemap needs proper ID. 
		genRandDistractors();
		writeStimObjId();
		writeStimSpec();
		return taskId;
	}

	private void assignGenParams(NoisyMStickPngPsychometricTrialGenData trialGenData) {
		this.trialGenData = trialGenData;
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
			for(int i=0; i<numDistractors.numPsychometricDistractors; i++) {
				objs_randDistractor.add(new AllenMatchStick());
			}
			boolean randDistractorsSuccess = false;
			Boolean[] randDistractorSuccess = new Boolean[numDistractors.numPsychometricDistractors];
			for(int b=0; b<randDistractorSuccess.length; b++) randDistractorSuccess[b]=false;
			for(int j=0; j<numDistractors.numPsychometricDistractors; j++) {
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

	List<String> randDistractorsPngPaths = new LinkedList<String>();
	private void drawRandDistractors() {
		List<String> sampleLabels = Arrays.asList(new String[] {"sample"});
		int indx=0;
		for (AllenMatchStick obj: objs_randDistractor) {
			String path = gen.pngMaker.createAndSavePNGFromObj(obj, stimObjIds.getRandDistractorsIds().get(indx), sampleLabels);
			randDistractorsPngPaths.add(path);
		}
	}

	private void writeStimObjId() {
		//COORDS
		sampleCoords = randomWithinRadius(trialGenData.sampleDistanceLowerLim, trialGenData.sampleDistanceUpperLim);
		DistancedDistractorsUtil ddUtil = new DistancedDistractorsUtil(numChoices, trialGenData.choiceDistanceLowerLim, trialGenData.choiceDistanceUpperLim, 0, 0);
		distractorsCoords = (ArrayList<Coordinates2D>) ddUtil.getDistractorCoordsAsList();
		matchCoords = ddUtil.getMatchCoords();

		//SAMPLE SPEC
		NoisyPngSpec sampleSpec = new NoisyPngSpec();
		sampleSpec.setPath(psychometricPathAssigner.samplePngPath);
		sampleSpec.setNoiseMapPath(noiseMapPath);
		sampleSpec.setxCenter(sampleCoords.getX());
		sampleSpec.setyCenter(sampleCoords.getY());
		ImageDimensions sampleDimensions = new ImageDimensions(trialGenData.sampleScale, trialGenData.sampleScale);
		sampleSpec.setImageDimensions(sampleDimensions);
		MStickStimObjData sampleMStickObjData = new MStickStimObjData("Sample", sampleMStickSpec);
		dbUtil.writeStimObjData(stimObjIds.getSampleId(), sampleSpec.toXml(), sampleMStickObjData.toXml());

		//MATCH SPEC
		NoisyPngSpec matchSpec = new NoisyPngSpec();
		matchSpec.setPath(psychometricPathAssigner.matchPngPath);
		matchSpec.setxCenter(matchCoords.getX());
		matchSpec.setyCenter(matchCoords.getY());
		ImageDimensions matchDimensiosn = new ImageDimensions(trialGenData.sampleScale, trialGenData.sampleScale);
		matchSpec.setImageDimensions(matchDimensiosn);
		MStickStimObjData matchMStickObjData = new MStickStimObjData("Match", matchMStickSpec);
		dbUtil.writeStimObjData(stimObjIds.getMatchId(), matchSpec.toXml(), matchMStickObjData.toXml());

		//DISTRACTORS SPECS
		int indx=0;
		for(String psychometricPngPath : psychometricPathAssigner.getDistractorsPngPaths()) {
			NoisyPngSpec distractorSpec = new NoisyPngSpec();
			distractorSpec.setPath(psychometricPathAssigner.distractorsPngPaths.get(indx));
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
			distractorSpec.setPath(randDistractorsPngPaths.get(indx));
			distractorSpec.setxCenter(distractorsCoords.get(indx).getX());
			distractorSpec.setyCenter(distractorsCoords.get(indx).getY());
			ImageDimensions distractorDimensions = new ImageDimensions(trialGenData.sampleScale, trialGenData.sampleScale);
			distractorSpec.setImageDimensions(distractorDimensions);
			MStickStimObjData distractorMStickObjData = new MStickStimObjData("Distractor", matchMStickSpec);
			dbUtil.writeStimObjData(stimObjIds.getPsychometricDistractorsIds().get(indx), distractorSpec.toXml(), distractorMStickObjData.toXml());
			indx++;
		}
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
		choiceIds[0] = stimObjIds.getMatchId();
		for (int distractorIdIndx=0; distractorIdIndx<stimObjIds.getAllDistractorsIds().size(); distractorIdIndx++) {
			choiceIds[distractorIdIndx+1] = stimObjIds.getAllDistractorsIds().get(distractorIdIndx);
		}
		NAFCStimSpecSpec stimSpec = new NAFCStimSpecSpec(targetEyeWinCoords.toArray(new Coordinates2D[0]), targetEyeWinSizes, stimObjIds.getSampleId(), choiceIds, eStimObjData, rewardPolicy, rewardList);
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

	private String generateNoiseMap() {
		List<String> noiseMapLabels = new LinkedList<String>();
		noiseMapLabels.add(Long.toString(psychometricPathAssigner.sampleSetId));
		noiseMapLabels.add(Integer.toString(psychometricPathAssigner.sampleStimId));
		return gen.pngMaker.createAndSaveNoiseMapFromObj(sampleObj, stimObjIds.getSampleId(), noiseMapLabels);
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
	 * @param psychometricIds.getSetId()
	 * @param psychometricIds.getStimId()
	 */
	private void assignParamsForNoiseMapGen(double[] noiseChance) {
		noiseData = new NoiseData(NoiseType.PRE_JUNC, NoisyMStickPngPsychometricBlockGen.noiseNormalizedPosition_PRE_JUNC, noiseChance);
		sampleObj.setNoiseParameters(noiseData);
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

	public List<AllenMatchStick> getObjs_randDistractor() {
		return objs_randDistractor;
	}

	public void setObjs_randDistractor(List<AllenMatchStick> objs_randDistractor) {
		this.objs_randDistractor = objs_randDistractor;
	}






}