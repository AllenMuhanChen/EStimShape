package org.xper.allen.nafc.blockgen.rand;


import java.io.File;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;


import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.RandTrialNoiseMapGenerator;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricTrialGenerator;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.allen.nafc.vo.NoiseForm;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.allen.saccade.db.vo.StimSpecEntryUtil;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.db.vo.StimSpecEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.util.FileUtil;

import static junit.framework.Assert.assertEquals;
import static junit.framework.Assert.assertTrue;
import static org.junit.Assert.assertNotNull;

public class RandTrialTest {

	AbstractMStickPngTrialGenerator generator;
	NumberOfDistractorsForRandTrial numDistractors;
	NumberOfMorphCategories numMorphCategories;
	NoiseType noiseType;
	double[] noiseChance;

	RandNoisyTrialParameters trialParameters;
	RandTrial trial;



	@Before
	public void givenTestTrialFromPsychometric() {
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		generator = (PsychometricBlockGen) context.getBean(AbstractPsychometricTrialGenerator.class);
		int numQMDistractors = 1;
		int numRandDistractors = 1;
		numDistractors = new NumberOfDistractorsForRandTrial(numQMDistractors, numRandDistractors);
		int numMMCategories = 1;
		int numQMCategories = 1;
		numMorphCategories = new NumberOfMorphCategories(numMMCategories, numQMCategories);
		noiseType = NoiseType.NONE;
		noiseChance = new double[] {0.5,0.5};

		Lims sampleDistanceLims = new Lims(0,5);
		Lims choiceDistanceLims = new Lims(10,10);
		double size = 10;
		double eyeWinSize = 10;
		NoiseParameters noiseParameters = new NoiseParameters(noiseType, new double[] {0,0}, noiseChance);

		trialParameters = new RandNoisyTrialParameters(
				sampleDistanceLims,
				choiceDistanceLims,
				size,
				eyeWinSize,
				noiseParameters,
				numDistractors,
				numMorphCategories);

		trial = new RandTrial(
				generator,
				trialParameters);
		
	}


	@Test
	public void stimObj_ids_are_in_ascending_order() {
		Rand<Long> stimObjIds = getStimObjIds();

		//Assert
		assertTrue(stimObjIds.getSample() < stimObjIds.getMatch());
		assertTrue(stimObjIds.getMatch()< stimObjIds.getAllDistractors().get(0));

		int indx=0;
		for(int i=0; i<stimObjIds.getAllDistractors().size()-1;i++) {
			Long firstId = stimObjIds.getAllDistractors().get(i);
			Long nextId = stimObjIds.getAllDistractors().get(indx+1);
			assertTrue(firstId < nextId); 
		}
	}

	private Rand<Long> getStimObjIds() {
		//Assign
		StimObjIdAssignerForRandTrials stimObjIdAssigner = new StimObjIdAssignerForRandTrials(generator.getGlobalTimeUtil(), numDistractors);

		//Act
		Rand<Long> stimObjIds = stimObjIdAssigner.getStimObjIds();
		return stimObjIds;
	}


	@Test
	public void msticks_have_correct_component_numbers() {
		Rand<AllenMatchStick> mSticks = getMSticks();


		mStick_has_legal_component_numbers(mSticks.getSample());
		mStick_has_special_end(mSticks.getSample());
		mStick_has_legal_component_numbers(mSticks.getMatch());
		mStick_has_special_end(mSticks.getMatch());
		assertTrue(mSticks.getQualitativeMorphDistractors().size()>0);
		for (AllenMatchStick qmDistractor: mSticks.getQualitativeMorphDistractors()) {
			mStick_has_legal_component_numbers(qmDistractor);
			mStick_has_special_end(qmDistractor);
		}
		for (AllenMatchStick randDistractor: mSticks.getRandDistractors()) {
			mStick_has_legal_component_numbers(randDistractor);
		}
	}

	private Rand<AllenMatchStick> getMSticks() {
		MStickGeneratorForRandTrials mStickGenerator = new MStickGeneratorForRandTrials(
				generator,
				trialParameters);

		Rand<AllenMatchStick> mSticks = mStickGenerator.getmSticks();
		return mSticks;
	}

	private void mStick_has_legal_component_numbers(AllenMatchStick mStick) {
		assertTrue(mStick.getComp().length>=2);
		assertTrue(mStick.getnEndPt() >= 2);
		assertTrue(mStick.getnJuncPt() >=1);
		assertNotNull(mStick.getObj1());
		assertTrue(mStick.getBaseComp()>0);
		assertTrue(mStick.getSpecialEndComp().size()>0);
	}

	private void mStick_has_special_end(AllenMatchStick mStick) {
		assertTrue(mStick.getSpecialEnd().size()>0);
	}

	@Test
	public void mSticks_have_specs_generated() { //TODO: needs to be improved
		Rand<AllenMStickSpec> mStickSpecs = getmStickSpecs();

		AllenMStickSpec sampleSpec = mStickSpecs.getSample();
		AllenMStickSpec testSpec = AllenMStickSpec.fromXml(sampleSpec.toXml());

		assertNotNull(testSpec);
	}

	private Rand<AllenMStickSpec> getmStickSpecs() {
		MStickGeneratorForRandTrials mStickGenerator = new MStickGeneratorForRandTrials(
				generator,
				trialParameters);
		Rand<AllenMStickSpec> mStickSpecs = mStickGenerator.getmStickSpecs();
		return mStickSpecs;
	}

	@Test
	public void mSticks_draw_as_pngs(){
		Rand<AllenMatchStick> mSticks = getMSticks();
		Rand<Long> stimObjIds = getStimObjIds();


		Rand<String> pngPaths = drawPNGs(mSticks, stimObjIds);


		assertFileExists(pngPaths.getSample());
		assertFileExists(pngPaths.getMatch());
		for(String path:pngPaths.getAllDistractors()){
			assertFileExists(path);
		}
	}

	private void assertFileExists(String pngPaths) {
		File sample = new File(pngPaths);
		assertTrue(sample.exists());
	}

	private Rand<String> drawPNGs(Rand<AllenMatchStick> mSticks, Rand<Long> stimObjIds) {
		PNGDrawerForRandTrial drawer = new PNGDrawerForRandTrial(
				generator,
				mSticks,
				stimObjIds
		);
		Rand<String> pngPaths = drawer.getPngPaths();
		return pngPaths;
	}

	@Test
	public void mSticks_generate_noiseMaps() {
		//Arrange
		long id = 1L;
		generator.getPngMaker().createDrawerWindow();
		MStickGeneratorForRandTrials mStickGenerator = new MStickGeneratorForRandTrials(
				generator,
				trialParameters);
		AllenMatchStick mStick = mStickGenerator.getSample();
		NoiseParameters noiseParameters = new NoiseParameters(new NoiseForm(noiseType, new double[] {0,0.8}), noiseChance);
		RandTrialNoiseMapGenerator noiseMapGenerator = new RandTrialNoiseMapGenerator(id, mStick, noiseParameters, generator);
		generator.getPngMaker().close();
		
		//Act
		String path = noiseMapGenerator.getNoiseMapPath();
		
		//Assert
		assertFileExists(path);
	}

	@Test
	public void coords_are_radially_spaced() {
		RandTrialCoordinateAssigner coordAssigner = new RandTrialCoordinateAssigner(trialParameters.getSampleDistanceLims(), trialParameters.getNumDistractors());
		
		Rand<Coordinates2D> coords = coordAssigner.getCoords();
		
		coords_have_same_distance_from_origin(coords);

	}


	private void coords_have_same_distance_from_origin(Rand<Coordinates2D> coords) {
		Coordinates2D origin = new Coordinates2D(0,0);
		List<Coordinates2D> choices = new LinkedList<Coordinates2D>();
		choices.add(coords.getMatch());
		choices.addAll(coords.getAllDistractors());
		
		List<Long> radii = new LinkedList<Long>(); 
		for(Coordinates2D choice: choices) {
			radii.add(Math.round(choice.distance(origin)*100)/100);
		}
		
		assertTrue(Collections.frequency(radii, radii.get(0)) == radii.size());
	}
	

	@Test
	public void stim_obj_data() {
		String noiseMapPath = "foo";
		MStickGeneratorForRandTrials mStickGenerator = new MStickGeneratorForRandTrials(
				generator,
				trialParameters);

		Rand<AllenMatchStick> mSticks = mStickGenerator.getmSticks();
		Rand<AllenMStickSpec> mStickSpecs = mStickGenerator.getmStickSpecs();
		Rand<Long> stimObjIds = getStimObjIds();
		Rand<String> pngPaths = drawPNGs(mSticks, stimObjIds);
		RandTrialCoordinateAssigner coordAssigner = new RandTrialCoordinateAssigner(trialParameters.getSampleDistanceLims(), trialParameters.getNumDistractors());
		Rand<Coordinates2D> coords = coordAssigner.getCoords();

		getmStickSpecs();
		RandTrialStimObjDataWriter stimObjDataWriter = new RandTrialStimObjDataWriter(
				noiseMapPath,
				generator.getDbUtil(),
				trialParameters,
				pngPaths,
				stimObjIds,
				mStickSpecs,
				coords
		);


		stimObjDataWriter.writeStimObjId();

		Long stimObjId = stimObjIds.getSample();
		NoisyPngSpec stimObjData = NoisyPngSpec.fromXml(generator.getDbUtil().readStimObjData(stimObjId).getSpec());
		assertEquals(stimObjData.getPngPath(), pngPaths.getSample());


//		StimSpecEntry entry = generator.getDbUtil().readStimObjData(stimObjIds.getSample());
//		StimSpecEntryUtil sseu = new StimSpecEntryUtil(entry);
//		NAFCStimSpecSpec stimObjSpec = sseu.NAFCStimSpecSpecFromXmlSpec();

	}

	@Test
	public void generates_stimSpec(){

	}

}
