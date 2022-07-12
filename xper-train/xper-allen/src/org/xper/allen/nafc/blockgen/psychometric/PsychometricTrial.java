package org.xper.allen.nafc.blockgen.psychometric;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.png.ImageDimensions;
import org.xper.allen.nafc.blockgen.NAFCMStickSpecs;
import org.xper.allen.nafc.blockgen.NAFCAllenMatchStickFetcher;
import org.xper.allen.nafc.blockgen.NAFCMatchSticks;
import org.xper.allen.nafc.blockgen.NAFCCoordinates;
import org.xper.allen.nafc.blockgen.NAFCPaths;
import org.xper.allen.nafc.blockgen.NumberOfDistractors;
import org.xper.allen.nafc.blockgen.PngBasePaths;
import org.xper.allen.nafc.blockgen.RandDistractorPNGGenerator;
import org.xper.allen.nafc.blockgen.StimObjIdAssignerForPsychometricTrials;
import org.xper.allen.nafc.blockgen.StimObjIdsForMixedPsychometricAndRand;
import org.xper.allen.nafc.blockgen.Trial;
import org.xper.allen.nafc.experiment.RewardPolicy;
import org.xper.allen.nafc.vo.MStickStimObjData;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;

/**
 * Main Class to write a PsychometricTrial to the database.
 */
public class PsychometricTrial implements Trial{
	/**
	 * Inputs
	 */
	AbstractPsychometricTrialGenerator generator;
	NumberOfDistractors numDistractors;
	PsychometricIds psychometricIds;
	double[] noiseChance;
	NoisyTrialParameters trialParameters;
	
	public PsychometricTrial(
			AbstractPsychometricTrialGenerator noisyMStickPngPsychometricBlockGen,
			NumberOfDistractors numDistractors, 
			PsychometricIds psychometricIds,
			double[] noiseChance,
			NoisyTrialParameters trialParameters) {

		this.generator = noisyMStickPngPsychometricBlockGen;
		this.numDistractors = numDistractors;
		this.psychometricIds = psychometricIds;
		this.noiseChance = noiseChance;
		this.trialParameters = trialParameters;

		dbUtil = generator.getDbUtil();
		this.numChoices = numDistractors.numTotal+1;
	}

	/**
	 * Private instance vars
	 */
	private AllenDbUtil dbUtil;
	int numChoices;
	String noiseMapPath;
	private Long taskId;
	NAFCCoordinates coords;
	NAFCPaths pngPaths;
	NAFCPaths specPaths;
	NAFCMStickSpecs mStickSpecs = new NAFCMStickSpecs();
	NAFCMatchSticks matchSticks = new NAFCMatchSticks();
	StimObjIdsForMixedPsychometricAndRand stimObjIds;

	
	/**
	 * Called before write() in order to do preallocation of parameters
	 * before the trial is assigned a taskId and written to the database
	 */
	@Override
	public void preWrite() {
		assignPsychometricPaths();
	}

	private void assignPsychometricPaths() {
		PngBasePaths psychometricBasePaths = new PngBasePaths(generator.getGeneratorPsychometricPngPath(), generator.getExperimentPsychometricPngPath(), generator.getGeneratorPsychometricSpecPath());
		PsychometricPathAssigner psychometricPathAssigner = PsychometricPathAssigner.createWithNewNAFCPngPathsObj(psychometricIds, numDistractors.numPsychometricDistractors, psychometricBasePaths);
		psychometricPathAssigner.assign();
		pngPaths = psychometricPathAssigner.getPngPaths();
		specPaths = psychometricPathAssigner.getSpecPaths();
	}

	@Override
	public void write() {
		assignStimObjIds();
		loadMSticks();
		generateNoiseMap();
		generateRandDistractors();
		assignCoords();
		writeStimObjDataSpecs();
		assignTaskId();
		writeStimSpec();
	}


	private void assignStimObjIds() {
		StimObjIdAssignerForPsychometricTrials stimObjIdAssigner = new StimObjIdAssignerForPsychometricTrials(generator.getGlobalTimeUtil(), numDistractors);
		stimObjIdAssigner.assignStimObjIds();
		stimObjIds = stimObjIdAssigner.getStimObjIds();
	}

	private void loadMSticks() {
		NAFCAllenMatchStickFetcher fetcher = new NAFCAllenMatchStickFetcher(generator, specPaths);
		mStickSpecs = fetcher.getmStickSpecs();
		matchSticks = fetcher.getMatchSticks();
	}

	private void generateNoiseMap() {
		PsychometricNoiseMapGenerator psychometricNoiseMapGenerator = 
				new PsychometricNoiseMapGenerator(
						matchSticks.getSampleMStick(),
						psychometricIds,
						generator,
						noiseChance,
						stimObjIds.getSampleId(),
						trialParameters.getNoiseParameters());
		noiseMapPath = psychometricNoiseMapGenerator.getNoiseMapPath();
	}

	List<String> randDistractorsPngPaths;
	List<AllenMatchStick> objs_randDistractors;

	private void generateRandDistractors() {
		RandDistractorPNGGenerator randDistractorPNGGenerator = new RandDistractorPNGGenerator(numDistractors, generator, stimObjIds.getRandDistractorsIds(), pngPaths.distractorsPaths);
		randDistractorPNGGenerator.genRandDistractors();
		randDistractorsPngPaths = randDistractorPNGGenerator.getRandDistractorsPngPaths();

		pngPaths.addToDistractors(randDistractorsPngPaths);
		objs_randDistractors = randDistractorPNGGenerator.getObjs_randDistractor();
	}

	private void assignCoords() {
		NAFCCoordinateAssigner coordAssigner = new NAFCCoordinateAssigner(
				trialParameters.getSampleDistanceLims(),
				numChoices);
		

		coords = coordAssigner.getCoords();
	}

	private void writeStimObjDataSpecs() {
		PsychometricStimObjSpecWriter stimObjSpecWriter = new PsychometricStimObjSpecWriter(
				numChoices,
				pngPaths,
				stimObjIds,
				noiseMapPath,
				dbUtil,
				mStickSpecs,
				trialParameters,
				coords);

		stimObjSpecWriter.writeStimObjId();
	}

	private void assignTaskId() {
		setTaskId(stimObjIds.getSampleId());
	}
	
	private void writeStimSpec() {
		PsychometricStimSpecWriter stimSpecWriter = new PsychometricStimSpecWriter(
				getTaskId(), 
				dbUtil,
				trialParameters,
				coords,
				numChoices,
				stimObjIds);
		
		stimSpecWriter.writeStimSpec();
	}

	public Long getTaskId() {
		return taskId;
	}

	public void setTaskId(Long taskId) {
		this.taskId = taskId;
	}

	public AbstractPsychometricTrialGenerator getGen() {
		return generator;
	}

	public void setGen(AbstractPsychometricTrialGenerator gen) {
		this.generator = gen;
	}

	public AllenDbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(AllenDbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public int getNumChoices() {
		return numChoices;
	}

	public void setNumChoices(int numChoices) {
		this.numChoices = numChoices;
	}


	public String getNoiseMapPath() {
		return noiseMapPath;
	}

	public void setNoiseMapPath(String noiseMapPath) {
		this.noiseMapPath = noiseMapPath;
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







}