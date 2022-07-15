package org.xper.allen.nafc.blockgen.psychometric;

import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.RandMStickGenerator;
import org.xper.allen.nafc.blockgen.PsychometricMStickFetcher;
import org.xper.allen.nafc.blockgen.NumberOfDistractorsForPsychometricTrial;
import org.xper.allen.nafc.blockgen.PngBasePaths;
import org.xper.allen.nafc.blockgen.Trial;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;

/**
 * Main Class to write a PsychometricTrial to the database.
 */
public class PsychometricTrial implements Trial{
	/**
	 * Inputs
	 */
	private AbstractPsychometricTrialGenerator generator;
	private NumberOfDistractorsForPsychometricTrial numDistractors;
	private PsychometricIds psychometricIds;
	private double[] noiseChance;
	private NoisyTrialParameters trialParameters;
	
	public PsychometricTrial(
			AbstractPsychometricTrialGenerator noisyMStickPngPsychometricBlockGen,
			NumberOfDistractorsForPsychometricTrial numDistractors,
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
	private int numChoices;
	private String noiseMapPath;
	private Long taskId;
	private Psychometric<Coordinates2D> coords;
	private Psychometric<String> pngPaths;
	private Psychometric<String> specPaths;
	private Psychometric<AllenMStickSpec> mStickSpecs = new Psychometric<AllenMStickSpec>();
	private Psychometric<AllenMatchStick> matchSticks = new Psychometric<AllenMatchStick>();;
	private Psychometric<Long> stimObjIds;

	
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
		drawRandDistractorsPNGs();
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
		PsychometricMStickFetcher fetcher = new PsychometricMStickFetcher(generator, specPaths);
		mStickSpecs = fetcher.getmStickSpecs();
		this.matchSticks = fetcher.getMatchSticks();
	}

	private void generateNoiseMap() {
		PsychometricNoiseMapGenerator psychometricNoiseMapGenerator = 
				new PsychometricNoiseMapGenerator(
						matchSticks.getSample(),
						psychometricIds,
						generator,
						noiseChance,
						stimObjIds.getSample(),
						trialParameters.getNoiseParameters());
		noiseMapPath = psychometricNoiseMapGenerator.getNoiseMapPath();
	}

	
	List<AllenMatchStick> objs_randDistractors = new LinkedList<AllenMatchStick>();

	private void generateRandDistractors() {
		for(int i=0; i<numDistractors.numRandDistractors; i++) {
			RandMStickGenerator randGenerator = new RandMStickGenerator(generator.getMaxImageDimensionDegrees());
			matchSticks.addRandDistractor(randGenerator.getMStick());
			mStickSpecs.addRandDistractor(randGenerator.getMStickSpec());
		}
	}
	

	private void drawRandDistractorsPNGs() {
		List<String> randDistractorLabels = Arrays.asList(new String[] {"Rand Distractor"});
		int indx=0;
		for (AllenMatchStick obj: matchSticks.getRandDistractors()) {
			String path = generator.getPngMaker().createAndSavePNG(obj, stimObjIds.getRandDistractors().get(indx), randDistractorLabels, generator.getGeneratorPngPath());
			generator.convertPathToExperiment(path);
			pngPaths.addRandDistractor(path);
			
		}
	}

	private void assignCoords() {
		PsychometricCoordinateAssigner coordAssigner = new PsychometricCoordinateAssigner(
				trialParameters.getSampleDistanceLims(),
				numDistractors, trialParameters.getChoiceDistanceLims());
		

		coords = coordAssigner.getCoords();
	}

	private void writeStimObjDataSpecs() {
		PsychometricStimObjDataWriter stimObjDataWriter = new PsychometricStimObjDataWriter(
				noiseMapPath,
				dbUtil,
				trialParameters,
				pngPaths,
				stimObjIds,
				mStickSpecs,
				coords
		);

		stimObjDataWriter.writeStimObjId();
	}

	private void assignTaskId() {
		setTaskId(stimObjIds.getSample());
	}
	
	private void writeStimSpec() {
		NAFCStimSpecWriter stimSpecWriter = new NAFCStimSpecWriter(
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

	private void setTaskId(Long taskId) {
		this.taskId = taskId;
	}

	public AbstractPsychometricTrialGenerator getGenerator() {
		return generator;
	}


	public NumberOfDistractorsForPsychometricTrial getNumDistractors() {
		return numDistractors;
	}


	public PsychometricIds getPsychometricIds() {
		return psychometricIds;
	}

	public double[] getNoiseChance() {
		return noiseChance;
	}


	public NoisyTrialParameters getTrialParameters() {
		return trialParameters;
	}

	public AllenDbUtil getDbUtil() {
		return dbUtil;
	}


	public int getNumChoices() {
		return numChoices;
	}


	public String getNoiseMapPath() {
		return noiseMapPath;
	}


	public Psychometric<Coordinates2D> getCoords() {
		return coords;
	}

	public Psychometric<String> getPngPaths() {
		return pngPaths;
	}


	public Psychometric<String> getSpecPaths() {
		return specPaths;
	}



	public Psychometric<Long> getStimObjIds() {
		return stimObjIds;
	}











}