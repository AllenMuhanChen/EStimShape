package org.xper.allen.nafc.blockgen.psychometric;

import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.*;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.util.FileUtil;

import java.io.File;
import java.util.Arrays;
import java.util.List;

import static org.junit.Assert.*;

public class PsychometricTrialListFactoryTest {

    @Test
    public void generates_proper_amount_of_trials(){
        //ARRANGE
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));

        AbstractPsychometricTrialGenerator generator = (PsychometricBlockGen) context.getBean(AbstractPsychometricTrialGenerator.class);

        NumberOfDistractorsForPsychometricTrial numDistractors = new NumberOfDistractorsForPsychometricTrial(
                1,1);

        NoisyTrialParameters trialParameters1 = new NoisyTrialParameters(
                new Lims(5,10),
                new Lims(5,10),
                10,
                10,
                new NoiseParameters(NoiseType.NONE, new double[]{0.3, 0.5},new double[]{0.3, 0.5} )
        );
        NoisyTrialParameters trialParameters2 = new NoisyTrialParameters(
                new Lims(5,10),
                new Lims(5,10),
                10,
                10,
                new NoiseParameters(NoiseType.POST_JUNC, new double[]{0.3, 0.5},new double[]{0.3, 0.5} )
        );

        TypeFrequency<NumberOfDistractorsForPsychometricTrial> numDistractorsTypeFrequency
                = new TypeFrequency<>(
                        Arrays.asList(numDistractors),
                        Arrays.asList(1.0));

        TypeFrequency<NoisyTrialParameters> trialParametersTypeFrequency =
                new TypeFrequency<>(
                        Arrays.asList(trialParameters1, trialParameters2),
                        Arrays.asList(0.3, 0.7)
                );

        PsychometricBlockGenParameters psychometricBlockGenParameters = new PsychometricBlockGenParameters(
                1,
                numDistractorsTypeFrequency,
                trialParametersTypeFrequency
        );

        PsychometricTrialListFactory psychometricFactory = new PsychometricTrialListFactory(
                generator,
                psychometricBlockGenParameters.getNumTrialsPerImage(),
                psychometricBlockGenParameters.getNumDistractorsTypeFrequency(),
                psychometricBlockGenParameters.getTrialParametersTypeFrequency()
        );


        //ACT
        List<Trial> trials = psychometricFactory.createTrials();


        //ASSERT
        File path = new File(generator.getGeneratorPsychometricPngPath());
        int numPngs = path.list().length;


        assertEquals(trials.size(),numPngs);
    }
}