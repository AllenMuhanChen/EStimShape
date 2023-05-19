package org.xper.allen.nafc.blockgen.psychometric;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.util.*;

import junit.framework.Assert;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NoiseFormer;
import org.xper.allen.nafc.blockgen.NumberOfDistractorsForPsychometricTrial;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.db.vo.StimSpecEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.time.TestTimeUtil;
import org.xper.util.FileUtil;

import javax.vecmath.Point2d;

public class PsychometricStimIntegrationTest {
	PsychometricBlockGen generator;
	int numPsychometricDistractors;
	int numRandDistractors;
	NumberOfDistractorsForPsychometricTrial numDistractors;
	long setId;
	int stimId;
	List<Integer> stimIds;
	PsychometricIds psychometricIds;
	Lims noiseChance;
	NoiseParameters noiseParameters;
	Lims sampleDistanceLims;
	Lims choiceDistanceLims;
	double size;
	double eyeWinSize;
	NoisyTrialParameters trialParameters;

	PsychometricStim trial;
	private Long sampleId;
	private Long matchId;
	private List<Long> psychometricDistractorIds;
	private List<Long> randDistractorIds;

	private NoisyPngSpec matchSpec;
	private NoisyPngSpec sampleSpec;
	private List<NoisyPngSpec> qmDistractorSpecs;
	private List<NoisyPngSpec> randDistractorSpecs;
	private List<Integer> distractorsStimIds;

	@Test
	public void generates_psychometric_trials_from_filesystem(){
		//Arrange
		givenTestSet();

		//Act
		trial.preWrite();
		trial.writeStim();

		//Assert
		thenPsychometricFilesFound();
		thenDrawsPngs();
		thenWritesStimObj();
		thenWritesStimSpec();
	}

	private void givenTestSet() {


		//THESE MUST EXIST IN FILE SYSTEM FOR TEST TO WORK
		setId = 1653428280110274L;
		stimId = 0;
		//LOOK ABOVE

		numPsychometricDistractors = 2;
		numRandDistractors = 1;

		FileUtil.loadTestSystemProperties("/xper.properties.psychometric");

		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.config_class"));

		generator = (PsychometricBlockGen) context.getBean(AbstractPsychometricTrialGenerator.class);
		TestTimeUtil timeUtil = new TestTimeUtil();
		generator.setGlobalTimeUtil(timeUtil);
		sampleId = timeUtil.getTestTime();
		matchId = sampleId + 1;
		psychometricDistractorIds = new LinkedList<>();
		for (int i = 0; i < numPsychometricDistractors; i++) {
			psychometricDistractorIds.add(matchId + 1 + i);
		}
		randDistractorIds = new LinkedList<>();
		for (int i = 0; i < numRandDistractors; i++) {
			randDistractorIds.add(matchId + 1 + numPsychometricDistractors + i);
		}


		NumberOfDistractorsForPsychometricTrial numDistractors = new NumberOfDistractorsForPsychometricTrial(numPsychometricDistractors, numRandDistractors);

		stimIds = Arrays.asList(0,1,2);
		psychometricIds = new PsychometricIds(setId, stimId, stimIds);

		List<Integer> stimIdsRemaining = new LinkedList<>(psychometricIds.allStimIds);
		stimIdsRemaining.remove(psychometricIds.allStimIds.indexOf(psychometricIds.stimId));
		distractorsStimIds = stimIdsRemaining.subList(0, numPsychometricDistractors);



		noiseChance = new Lims(0.5 ,0.8);
		noiseParameters = new NoiseParameters(NoiseFormer.getNoiseForm(NoiseType.PRE_JUNC), noiseChance);

		sampleDistanceLims = new Lims(9, 10);
		choiceDistanceLims = new Lims(4, 5);
		size = 8;
		eyeWinSize = 12;
		trialParameters =
				new NoisyTrialParameters(
						sampleDistanceLims,
						choiceDistanceLims,
						size,
						eyeWinSize,
						noiseParameters);
		PsychometricTrialParameters psychometricTrialParameters = new PsychometricTrialParameters(trialParameters, numDistractors, psychometricIds);
		trial = new PsychometricStim(generator, psychometricTrialParameters);
	}

	private void thenPsychometricFilesFound() {
		thenPngPathsAreCorrect();
		thenSpecFilesExist();
	}


	private void thenPngPathsAreCorrect() {
		thenSamplePngPathIsCorrect();
		thenMatchPngPathIsCorrect();
		thenDistractorPngPathsAreCorrect();
	}

	private void thenDrawsPngs(){
		List<String> randDistractorsPaths = getGeneratorRandDistractorPaths();
		assertFilesExist(randDistractorsPaths);
		assertFileExists(getPsychometricGeneratorNoiseMapPath());
	}

	private void thenWritesStimObj(){
		sampleSpec = getPngSpec(sampleId);
		matchSpec = getPngSpec(matchId);
		qmDistractorSpecs = getPngSpecs(psychometricDistractorIds);
		randDistractorSpecs = getPngSpecs(randDistractorIds);

		assertSpecDetails(sampleSpec, sampleDistanceLims, getPsychometricExperimentSamplePath());
		assertEquals(sampleSpec.getNoiseMapPath(), getPsychometricExperimentNoiseMapPath());

		assertSpecDetails(matchSpec, choiceDistanceLims, getPsychometricExperimentMatchPath());
		int i = 0;
		for (NoisyPngSpec spec : qmDistractorSpecs) {
			assertSpecDetails(spec, choiceDistanceLims, getPsychometricExperimentPsychometricDistractorPaths());
			i++;
		}
		i = 0;
		for (NoisyPngSpec spec : randDistractorSpecs) {
			assertSpecDetails(spec, choiceDistanceLims, getExperimentRandDistractorPaths().get(i));
			i++;
		}
	}

	private List<NoisyPngSpec> getPngSpecs(List<Long> ids) {
		List<NoisyPngSpec> specs = new LinkedList<>();
		for (Long id : ids) {
			specs.add(getPngSpec(id));
		}
		return specs;
	}

	private NoisyPngSpec getPngSpec(long id) {
		StimSpecEntry entry = generator.getDbUtil().readStimObjData(id);
		NoisyPngSpec spec = NoisyPngSpec.fromXml(entry.getSpec());
		return spec;
	}

	private void assertSpecDetails(NoisyPngSpec spec, Lims distanceLims, String expectedPngPath) {
		assertLocationWithinBounds(spec, distanceLims);
		Assert.assertTrue(spec.getDimensions().getWidth() == size);
		Assert.assertTrue(spec.getPngPath().equals(expectedPngPath));
		Assert.assertTrue(spec.getAlpha() == 1);

	}

	private void assertSpecDetails(NoisyPngSpec spec, Lims distanceLims, List<String> possiblePaths) {
		assertLocationWithinBounds(spec, distanceLims);
		Assert.assertTrue(spec.getDimensions().getWidth() == size);
		Assert.assertTrue(possiblePaths.contains(spec.getPath()));
		Assert.assertTrue(spec.getAlpha() == 1);
	}


	private void thenWritesStimSpec(){
		StimSpecEntry sse = generator.getDbUtil().readStimSpec(sampleId);
		NAFCStimSpecSpec stimSpec = NAFCStimSpecSpec.fromXml(sse.getSpec());
		target_eye_window_coords_match_with_stimuli(stimSpec);
		rewarded_trial_is_match(stimSpec);
	}

	private void target_eye_window_coords_match_with_stimuli(NAFCStimSpecSpec stimSpec) {
		Coordinates2D matchCoords = new Coordinates2D(matchSpec.getxCenter(), matchSpec.getyCenter());
		Assert.assertTrue(stimSpec.getTargetEyeWinCoords()[0].equals(matchCoords));
		for(int i=1; i<numPsychometricDistractors; i++){
			NoisyPngSpec psychometricDistractorSpec = qmDistractorSpecs.get(i - 1);
			Coordinates2D psychometricDistractorCoords = new Coordinates2D(psychometricDistractorSpec.getxCenter(), psychometricDistractorSpec.getyCenter());
			Assert.assertTrue(stimSpec.getTargetEyeWinCoords()[i].equals(psychometricDistractorCoords));
		}
		for(int i=2+numPsychometricDistractors; i<numRandDistractors; i++){
			NoisyPngSpec randDistractorSpec = randDistractorSpecs.get(i - (2+numPsychometricDistractors));
			Coordinates2D randDistractorCoords = new Coordinates2D(randDistractorSpec.getxCenter(), randDistractorSpec.getyCenter());
			Assert.assertTrue(stimSpec.getTargetEyeWinCoords()[i].equals(randDistractorCoords));
		}
	}

	private void rewarded_trial_is_match(NAFCStimSpecSpec stimSpec) {
		int rewarded = stimSpec.getRewardList()[0];
		Assert.assertTrue(stimSpec.getChoiceObjData()[rewarded]==matchId);
	}

	private static void assertLocationWithinBounds(NoisyPngSpec actualSpec, Lims distanceLims) {
		Point2d location = new Point2d(actualSpec.getxCenter(), actualSpec.getyCenter());
		double radius = location.distance(new Point2d(0, 0));
		Assert.assertTrue((double) radius <= distanceLims.getUpperLim());
		Assert.assertTrue((double) radius >= distanceLims.getLowerLim());
	}

	private String getPsychometricGeneratorNoiseMapPath(){
		return generator.getGeneratorPsychometricNoiseMapPath() + "/" + Long.toString(sampleId) + "_noisemap_" + Long.toString(setId) + "_" + Integer.toString(stimId) +".png";
	}

	private String getPsychometricExperimentNoiseMapPath(){
		return generator.getExperimentPsychometricNoiseMapPath() + "/" + Long.toString(sampleId) + "_noisemap_" + Long.toString(setId) + "_" + Integer.toString(stimId) +".png";
	}


	private List<String> getPsychometricExperimentPsychometricDistractorPaths() {
		List<String> qmDistractorPaths = new LinkedList<>();
		for (Integer stId: distractorsStimIds) {
			String path = generator.getExperimentPsychometricPngPath() + "/" + Long.toString(setId) + "_" + Integer.toString(stId) + ".png";
			qmDistractorPaths.add(path);
		}
		return qmDistractorPaths;
	}

	private String getPsychometricExperimentSamplePath() {
		String samplePath = generator.getExperimentPsychometricPngPath() + "/" + Long.toString(setId) + "_" + Integer.toString(stimId) + ".png";
		return samplePath;
	}

	private String getPsychometricExperimentMatchPath() {
		return generator.getExperimentPsychometricPngPath() + "/" + Long.toString(setId) + "_" + Integer.toString(stimId) + ".png";
	}



	private List<String> getGeneratorRandDistractorPaths() {
		List<String> randDistractorPaths = new LinkedList<>();
		for (int i = 0; i < numRandDistractors; i++) {
			String path = generator.getGeneratorPngPath() + "/" + Long.toString(randDistractorIds.get(i)) + "_randDistractor.png";
			randDistractorPaths.add(path);
		}
		return randDistractorPaths;
	}

	private List<String> getExperimentRandDistractorPaths() {
		List<String> randDistractorPaths = new LinkedList<>();
		for (int i = 0; i < numRandDistractors; i++) {
			String path = generator.getExperimentPngPath() + "/" + Long.toString(randDistractorIds.get(i)) + "_randDistractor.png";
			randDistractorPaths.add(path);
		}
		return randDistractorPaths;
	}

	private void thenSamplePngPathIsCorrect() {
		String path = trial.getPngPaths().getSample();
		String expectedSamplePath = generator.getExperimentPsychometricPngPath()+"/"+setId+"_"+stimId+".png";

		assertEquals(expectedSamplePath, path);
		fileExists(path);
	}

	private void thenMatchPngPathIsCorrect() {
		String path = trial.getPngPaths().getMatch();
		String expectedMatchPath = generator.getExperimentPsychometricPngPath()+"/"+setId+"_"+stimId+".png";
		assertEquals(expectedMatchPath, path);
		fileExists(path);
	}
	private void thenDistractorPngPathsAreCorrect() {
		List<String> expectedDistractorPaths = new ArrayList<String>();
		for(int i=1;i<stimIds.size();i++) {
			expectedDistractorPaths.add(generator.getExperimentPsychometricPngPath()+"/"+setId+"_"+stimIds.get(i)+".png");
		}
		for(String actualPath : trial.getPngPaths().getPsychometricDistractors()) {
			assertTrue(expectedDistractorPaths.contains(actualPath));
			fileExists(actualPath);
		}
	}

	private void thenSpecFilesExist() {
		fileExists(trial.getSpecPaths().getSample());
		fileExists(trial.getSpecPaths().getMatch());
		for (String path: trial.getSpecPaths().getAllDistractors()) {
			fileExists(path);
		}
	}

	private void fileExists(String path) {

		File file = new File(path);
		assertTrue("specFile does not exist. Looking for " + path,file.exists());
	}


	private void assertFilesExist(List<String> paths) {
		for (String path : paths) {
			assertFileExists(path);
		}
	}


	private void assertFileExists(String pngPaths) {
		File sample = new File(pngPaths);
		Assert.assertTrue(sample.exists());
	}



}