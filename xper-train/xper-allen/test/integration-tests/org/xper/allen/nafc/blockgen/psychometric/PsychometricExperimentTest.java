package org.xper.allen.nafc.blockgen.psychometric;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.drawing.composition.noisy.NoisePositions;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;
import org.xper.allen.nafc.blockgen.NumberOfDistractorsForPsychometricTrial;
import org.xper.allen.nafc.blockgen.rand.NumberOfDistractorsForRandTrial;
import org.xper.allen.nafc.blockgen.rand.NumberOfMorphCategories;
import org.xper.allen.nafc.blockgen.rand.RandFactoryParameters;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.allen.util.AllenDbUtil;
import org.xper.intan.stimulation.*;
import org.xper.util.FileUtil;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class PsychometricExperimentTest {

    private PsychometricBlockGen gen;
    private AllenDbUtil dbUtil;

    @Before
    public void setUp() throws Exception {
        FileUtil.loadTestSystemProperties("/xper.properties.psychometric");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

        gen = context.getBean(PsychometricBlockGen.class);
        dbUtil = context.getBean(AllenDbUtil.class);
    }

    @Test
    public void gen_trials(){
        prepDb();

        //PSYCHOMETRIC
        int numTrialsPerImage = 1;
        NoiseParameters noiseParameters = new NoiseParameters(
                NoiseType.PRE_JUNC,
                new NoisePositions(0.0,1.0),
                new Lims(0,1)
        );
        NAFCTrialParameters nafcTrialParameters = new NAFCTrialParameters(
                new Lims(0.0,0.0),
                new Lims(8.0,8.0),
                8.0,
                8.0
        );
        NoisyTrialParameters noisyTrialParameters = new NoisyTrialParameters(noiseParameters, nafcTrialParameters);
        List<NoisyTrialParameters> trialParameters = Collections.singletonList(noisyTrialParameters);

        NumberOfDistractorsForPsychometricTrial numberOfDistractorsForPsychometricTrial = new NumberOfDistractorsForPsychometricTrial(
                3,
                0);
        List<NumberOfDistractorsForPsychometricTrial> numPsychometricDistractors = Collections.singletonList(numberOfDistractorsForPsychometricTrial);



        Map<RHSChannel, ChannelEStimParameters> eStimParametersForChannels = new HashMap<>();

        WaveformParameters waveformParameters = new WaveformParameters(
                StimulationShape.Biphasic,
                StimulationPolarity.NegativeFirst,
                5000.0,
                5000.0,
                0.0,
                50.0,
                50.0
        );
        PulseTrainParameters pulseTrainParameters = new PulseTrainParameters(
                PulseRepetition.SinglePulse,
                1,
                0.0,
                10.0
        );

        eStimParametersForChannels.put(RHSChannel.B025, new ChannelEStimParameters(waveformParameters, pulseTrainParameters));
        Map<Long, EStimParameters> eStimParametersForSetIds = new HashMap<>();
        EStimParameters eStimParameters = new EStimParameters(eStimParametersForChannels);
        eStimParametersForSetIds.put(1L, eStimParameters);

        PsychometricFactoryParameters psychometricFactoryParameters = PsychometricFactoryParameters.create(numTrialsPerImage, trialParameters, numPsychometricDistractors, eStimParametersForSetIds);

        //RAND
        RandFactoryParameters randFactoryParameters = new RandFactoryParameters(
                0,
                Collections.singletonList(new NumberOfDistractorsForRandTrial(0, 0)),
                Collections.singletonList(new NumberOfMorphCategories(0, 0)),
                Collections.singletonList(new NoisyTrialParameters(noisyTrialParameters))
        );


        PsychometricBlockParameters psychometricBlockParameters = new PsychometricBlockParameters(psychometricFactoryParameters, randFactoryParameters);



        gen.setUp(psychometricBlockParameters);
    }

    private void prepDb() {
        JdbcTemplate jt = new JdbcTemplate(dbUtil.getDataSource());
        jt.execute("TRUNCATE TABLE TaskToDo");
        jt.execute("TRUNCATE TABLE TaskDone");
        jt.execute("TRUNCATE TABLE StimSpec");
        jt.execute("TRUNCATE TABLE BehMsg");
        jt.execute("TRUNCATE TABLE BehMsgEye");
        jt.execute("TRUNCATE TABLE StimObjData");
        jt.execute("TRUNCATE TABLE ExpLog");
        jt.execute("TRUNCATE TABLE AcqData");
        jt.execute("TRUNCATE TABLE StimGaInfo");
        jt.execute("TRUNCATE TABLE LineageGaInfo");
    }
}