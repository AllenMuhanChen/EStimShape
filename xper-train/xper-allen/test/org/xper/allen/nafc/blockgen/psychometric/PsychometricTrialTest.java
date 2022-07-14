package org.xper.allen.nafc.blockgen.psychometric;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NumberOfDistractors;
import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricTrialGenerator;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricIds;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricTrial;
import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.util.FileUtil;

public class PsychometricTrialTest {
	PsychometricBlockGen generator;
	int numPsychometricDistractors;
	int numRandDistractors;
	NumberOfDistractors numDistractors;
	long setId;
	int stimId;
	List<Integer> stimIds;
	PsychometricIds psychometricIds;
	double[] noiseChance;
	NoiseParameters noiseParameters;
	Lims sampleDistanceLims;
	Lims choiceDistanceLims;
	double sampleScale;
	double eyeWinSize;
	NoisyTrialParameters trialParameters;

	PsychometricTrial trial;


	@Before
	public void givenTestTrial() {

		//THESE MUST EXIST IN FILE SYSTEM FOR TEST TO WORK
		setId = 1653428280110274L;
		stimId = 0;
		//LOOK ABOVE

		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		generator = (PsychometricBlockGen) context.getBean(AbstractPsychometricTrialGenerator.class);

		numPsychometricDistractors = 2;
		numRandDistractors = 1;
		NumberOfDistractors numDistractors = new NumberOfDistractors(numPsychometricDistractors, numRandDistractors);

		stimIds = Arrays.asList(0,1,2);
		psychometricIds = new PsychometricIds(setId, stimId, stimIds);


		noiseChance = new double[] {1,1};
		noiseParameters = new NoiseParameters(NoiseType.NONE, new double[] {0.5,1}, noiseChance);

		sampleDistanceLims = new Lims(10, 10);
		choiceDistanceLims = new Lims(5, 5);
		sampleScale = 8;
		eyeWinSize = 12;
		trialParameters = 
				new NoisyTrialParameters(
						sampleDistanceLims, 
						choiceDistanceLims,
						sampleScale,
						eyeWinSize,
						noiseParameters);

		trial = new PsychometricTrial(generator, numDistractors, psychometricIds, noiseChance, trialParameters);
	}


	@Test
	public void testGeneratorBeanGot() {
		assertEquals(PsychometricBlockGen.class, generator.getClass());
	}


	@Test
	public void testPreWrite() {
		trial.preWrite();

		thenPngPathsAreCorrect();
		thenSpecFilesExist();
	}


	private void thenPngPathsAreCorrect() {
		thenSamplePngPathIsCorrect();
		thenMatchPngPathIsCorrect();
		thenDistractorPngPathsAreCorrect();
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
		for(String actualPath : trial.getPngPaths().getAllDistractors()) {
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



	@Test
	public void testWriteExecutesAndSavesToDb() {
		generator.getPngMaker().createDrawerWindow();
		trial.preWrite();
		trial.write();
		long taskTodo = trial.getTaskId();
		randDistractorsGenerated();
		dBUpdated(taskTodo);
	}



	private void randDistractorsGenerated() {
		//Testing Objs
		List<AllenMatchStick> objs = trial.objs_randDistractors;
		for (AllenMatchStick obj:objs) {
			assertNotNull(obj.getComp()[1]);
		}

		//Testing .pngs
		for (String path: trial.getPngPaths().getAllDistractors()) {
			assertNotNull("distractor .png with path " + path + " does not exist",
					new File(path).exists());
		}
	}

	/**
	 * write()
	 * writes StimObjData and StimSpec
	 * @param expectedTaskTodo
	 */
	public void dBUpdated(long expectedTaskTodo) {
		//Test stimSpec
		long maxStimSpecId = generator.getDbUtil().readStimSpecMaxId();
		assertEquals(expectedTaskTodo, maxStimSpecId);
		//Test stimObjData
		List<Long> expectedStimObjIds = new ArrayList<Long>();
		expectedStimObjIds.add(trial.getStimObjIds().getSample());
		expectedStimObjIds.add(trial.getStimObjIds().getMatch());
		expectedStimObjIds.addAll(trial.getStimObjIds().getAllDistractors());

		assertEquals("The number of esxpected stimObjIds does not match the number generated by the class",
				2 + numRandDistractors+numPsychometricDistractors,expectedStimObjIds.size());
		for (Long expectedStimObjId: expectedStimObjIds) {
			assertNotNull("Expected StimObjId does not exist in db!", trial.getDbUtil().readStimObjData(expectedStimObjId));
		}
	}
	//	
	//	
	//	public void specFileExists(){
	//		String path = testTrial.psychometricPathAssigner.getMatchSpecPath();
	//			File file = new File(path);
	//			
	//			assertTrue("specFile does not exist. Looking for " + path,file.exists());
	//	}
	//	
	//
	//	public void sampleObjExists() {
	//		assertNotNull("SampleObj doesn't exist", testTrial.getSampleObj());
	//	}



}
