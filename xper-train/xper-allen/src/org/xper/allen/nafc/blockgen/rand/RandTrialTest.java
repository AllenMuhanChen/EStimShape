package org.xper.allen.nafc.blockgen.rand;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.util.List;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.FromRandLeafMStickGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphMStickGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricNoiseMapGenerator;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.util.FileUtil;

public class RandTrialTest {

	AbstractMStickPngTrialGenerator generator;
	NumberOfDistractorsByMorphType numDistractors;
	NumberOfMorphCategories numMorphCategories;
	NoiseType noiseType;
	double[] noiseChance;

	RandNoisyTrialParameters trialParameters;

	RandTrial trial;

	@Before
	public void givenTestTrialFromPsychometric() {
		JavaConfigApplicationContext context = new JavaConfigApplicationContext(
				FileUtil.loadConfigClass("experiment.ga.config_class"));

		generator = (PsychometricBlockGen) context.getBean(AbstractPsychometricNoiseMapGenerator.class);
		int numQMDistractors = 1;
		int numRandDistractors = 1;
		numDistractors = new NumberOfDistractorsByMorphType(numQMDistractors, numRandDistractors);
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
		//Assign
		StimObjIdAssignerForRandTrials stimObjIdAssigner = new StimObjIdAssignerForRandTrials(generator.getGlobalTimeUtil(), numDistractors);

		//Act
		StimObjIdsForRandTrial stimObjIds = stimObjIdAssigner.getStimObjIds();

		//Assert
		assertTrue(stimObjIds.getSampleId() < stimObjIds.getMatchId());
		assertTrue(stimObjIds.getMatchId()< stimObjIds.getAllDistractorIds().get(0));

		int indx=0;
		for(int i=0; i<stimObjIds.getAllDistractorIds().size()-1;i++) {
			Long firstId = stimObjIds.getAllDistractorIds().get(i);
			Long nextId = stimObjIds.getAllDistractorIds().get(indx+1);
			assertTrue(firstId < nextId); 
		}
	}


	@Test
	public void samples_have_correct_component_numbers() {
		NoisyMStickGeneratorForRandTrials mStickGenerator = new NoisyMStickGeneratorForRandTrials(
				generator,
				trialParameters);

		AllenMatchStick sample = mStickGenerator.getSample();

		assertNotNull(mStickGenerator.getSample());

		mStick_has_legal_component_numbers(sample);
	}

	private void mStick_has_legal_component_numbers(AllenMatchStick mStick) {
		assertTrue(mStick.getComp().length>=2);
		assertTrue(mStick.getnEndPt() >= 2);
		assertTrue(mStick.getnJuncPt() >=1);
		assertNotNull(mStick.getObj1());
		assertTrue(mStick.getBaseComp()>0);
		assertTrue(mStick.getSpecialEnd().size()>0);
		assertTrue(mStick.getSpecialEndComp().size()>0);
	}


	@Test
	public void matches_have_correct_component_numbers() {
		NoisyMStickGeneratorForRandTrials mStickGenerator = new NoisyMStickGeneratorForRandTrials(
				generator,
				trialParameters);


		AllenMatchStick match = mStickGenerator.getMatch();

		mStick_has_legal_component_numbers(match);
	}

	@Test
	public void qualitative_morph_distractors_have_correct_component_numbers() {
		NoisyMStickGeneratorForRandTrials mStickGenerator = new NoisyMStickGeneratorForRandTrials(
				generator,
				trialParameters);


		List<AllenMatchStick> qmDistractors = mStickGenerator.getQualitativeMorphDistractors();
		assertTrue(qmDistractors.size()>0);
		for (AllenMatchStick mStick: qmDistractors) {
			mStick_has_legal_component_numbers(mStick);
		}
	
	}
	
	


}
