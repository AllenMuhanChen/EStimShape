package org.xper.allen.nafc.blockgen.rand;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParameterGenerator;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;

import static junit.framework.Assert.assertTrue;
import static org.junit.Assert.assertNotNull;

public class MStickGeneratorForRandTrialsTest {

    private Rand<AllenMatchStick> mSticks;
    private Rand<AllenMStickSpec> mStickSpecs;
    private Lims sampleDistanceLims;
    private Lims choiceDistanceLims;
    private int size;
    private int eyeWinSize;
    private NoiseParameters noiseParameters;
    private double[] noiseChance;
    private NoiseType noiseType;
    private int numQMDistractors;
    private int numRandDistractors;
    private NumberOfDistractorsForRandTrial numDistractors;
    private int numMMCategories;
    private NumberOfMorphCategories numMorphCategories;
    private int numQMCategories;
    private RandNoisyTrialParameters trialParameters;
    private double maxImageDimensionDegrees;
    private QualitativeMorphParameterGenerator qmp;
    private MetricMorphParameterGenerator mmp;


    @Test
    public void given_classic_generation_parameters() {
        numQMDistractors = 1;
        numRandDistractors = 1;
        numDistractors = new NumberOfDistractorsForRandTrial(numQMDistractors, numRandDistractors);

        build_params_for_mstick_generator();


        //ACT
        MStickGeneratorForRandTrials generator = new MStickGeneratorForRandTrials(
                this.maxImageDimensionDegrees,
                trialParameters,
                mmp,
                qmp
        );

        //ASSERT
        Rand<AllenMatchStick> mSticks = generator.getmSticks();
        msticks_have_correct_component_numbers(mSticks);
        Rand<AllenMStickSpec> mStickSpecs = generator.getmStickSpecs();
        mSticks_have_specs_generated(mStickSpecs);

    }

    @Test
    public void given_no_qm_generation() {
        numQMDistractors = 0;
        numRandDistractors = 1;
        numDistractors = new NumberOfDistractorsForRandTrial(numQMDistractors, numRandDistractors);

        build_params_for_mstick_generator();


        //ACT
        MStickGeneratorForRandTrials generator = new MStickGeneratorForRandTrials(
                this.maxImageDimensionDegrees,
                trialParameters,
                mmp,
                qmp
        );

        //ASSERT
        Rand<AllenMatchStick> mSticks = generator.getmSticks();
        msticks_have_correct_component_numbers(mSticks);
        Rand<AllenMStickSpec> mStickSpecs = generator.getmStickSpecs();
        mSticks_have_specs_generated(mStickSpecs);

    }

    @Test
    public void given_no_rand_generation() {
        numQMDistractors = 1;
        numRandDistractors = 0;
        numDistractors = new NumberOfDistractorsForRandTrial(numQMDistractors, numRandDistractors);

        build_params_for_mstick_generator();


        //ACT
        MStickGeneratorForRandTrials generator = new MStickGeneratorForRandTrials(
                this.maxImageDimensionDegrees,
                trialParameters,
                mmp,
                qmp
        );

        //ASSERT
        Rand<AllenMatchStick> mSticks = generator.getmSticks();
        msticks_have_correct_component_numbers(mSticks);
        Rand<AllenMStickSpec> mStickSpecs = generator.getmStickSpecs();
        mSticks_have_specs_generated(mStickSpecs);

    }

    @Test
    public void given_many_generation() {
        numQMDistractors = 5;
        numRandDistractors = 5;
        numDistractors = new NumberOfDistractorsForRandTrial(numQMDistractors, numRandDistractors);

        build_params_for_mstick_generator();


        //ACT
        MStickGeneratorForRandTrials generator = new MStickGeneratorForRandTrials(
                this.maxImageDimensionDegrees,
                trialParameters,
                mmp,
                qmp
        );

        //ASSERT
        Rand<AllenMatchStick> mSticks = generator.getmSticks();
        msticks_have_correct_component_numbers(mSticks);
        Rand<AllenMStickSpec> mStickSpecs = generator.getmStickSpecs();
        mSticks_have_specs_generated(mStickSpecs);

    }

    private void build_params_for_mstick_generator() {
        maxImageDimensionDegrees = 10;
        sampleDistanceLims = new Lims(0, 5);
        choiceDistanceLims = new Lims(9, 10);
        size = 10;
        eyeWinSize = 10;
        noiseType = NoiseType.NONE;
        noiseChance = new double[]{0.5, 0.5};
        noiseParameters = new NoiseParameters(noiseType, new double[]{0, 0}, noiseChance);


        numMMCategories = 1;
        numQMCategories = 1;
        numMorphCategories = new NumberOfMorphCategories(numMMCategories, numQMCategories);

        trialParameters = new RandNoisyTrialParameters(
                sampleDistanceLims,
                choiceDistanceLims,
                size,
                eyeWinSize,
                noiseParameters,
                numDistractors,
                numMorphCategories);

        mmp = new MetricMorphParameterGenerator();
        qmp = new QualitativeMorphParameterGenerator(maxImageDimensionDegrees);
    }


    private void msticks_have_correct_component_numbers(Rand<AllenMatchStick> mSticks) {
        then_mStick_has_legal_component_numbers(mSticks.getSample());
        mStick_has_special_end(mSticks.getSample());
        then_mStick_has_legal_component_numbers(mSticks.getMatch());
        mStick_has_special_end(mSticks.getMatch());
        assertTrue(mSticks.getQualitativeMorphDistractors().size() == numQMDistractors);
        assertTrue(mSticks.getRandDistractors().size()== numRandDistractors);
        for (AllenMatchStick qmDistractor : mSticks.getQualitativeMorphDistractors()) {
            then_mStick_has_legal_component_numbers(qmDistractor);
            mStick_has_special_end(qmDistractor);
        }
        for (AllenMatchStick randDistractor : mSticks.getRandDistractors()) {
            then_mStick_has_legal_component_numbers(randDistractor);
        }
    }

    private void then_mStick_has_legal_component_numbers(AllenMatchStick mStick) {
        assertTrue(mStick.getComp().length >= 2);
        assertTrue(mStick.getnEndPt() >= 2);
        assertTrue(mStick.getnJuncPt() >= 1);
        assertNotNull(mStick.getObj1());
        assertTrue(mStick.getBaseComp() > 0);
        assertTrue(mStick.getSpecialEndComp().size() > 0);
    }

    private void mStick_has_special_end(AllenMatchStick mStick) {
        assertTrue(mStick.getSpecialEnd().size() > 0);
    }


    private void mSticks_have_specs_generated(Rand<AllenMStickSpec> mStickSpecs) { //TODO: needs to be improved

        AllenMStickSpec sampleSpec = mStickSpecs.getSample();
        AllenMStickSpec testSpec = AllenMStickSpec.fromXml(sampleSpec.toXml());

        assertNotNull(testSpec);
    }


}
