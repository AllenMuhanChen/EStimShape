package org.xper.intan.stimulation;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.XperConfig;
import org.xper.allen.util.AllenDbUtil;
import org.xper.time.TimeUtil;
import org.xper.util.FileUtil;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class WriteEStimSpecs {

    private AllenDbUtil dbUtil;
    private TimeUtil timeUtil;

    @Before
    public void setUp() throws Exception {
        List<String> libs = new ArrayList<String>();
        libs.add("xper");
        new XperConfig("", libs);

        FileUtil.loadTestSystemProperties("/xper.properties");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("experiment.config_class"));
        dbUtil = context.getBean(AllenDbUtil.class);

    }

    @Test
    public void write_anodic_and_cathodic_first_mix() throws Exception {
        long id_1 = 1L;
        long id_2 = 2L;

        List<RHSChannel> channels = new ArrayList<>();
        channels.add(RHSChannel.A024);
        channels.add(RHSChannel.A000);
        channels.add(RHSChannel.A006);


        StimulationShape shape = StimulationShape.Biphasic;
        double d1 = 200.0;
        double d2 = 200.0;
        double dp = 100.0;
        double a1 = 2.5;
        double a2 = 2.5;
        WaveformParameters waveformOne = new WaveformParameters(
                shape,
                StimulationPolarity.NegativeFirst,
                d1,
                d2,
                dp,
                a1,
                a2
        );
        WaveformParameters waveformTwo = new WaveformParameters(
                shape,
                StimulationPolarity.PositiveFirst,
                d1,
                d2,
                dp,
                a1,
                a2
        );



        PulseTrainParameters pulseTrainParameters = new PulseTrainParameters(
                PulseRepetition.SinglePulse,
                1,
                10.0,
                4000,
                TriggerEdgeOrLevel.Level,
                0.0);

        ChargeRecoveryParameters chargeRecoveryParameters = new ChargeRecoveryParameters(
                true,
                0.0,
                3000.0
        );
        ChannelEStimParameters channelEStimParameters_1 = new ChannelEStimParameters(
                waveformOne,
                pulseTrainParameters,
                new AmpSettleParameters(),
                chargeRecoveryParameters);

        ChannelEStimParameters channelEStimParameters_2 = new ChannelEStimParameters(
                waveformTwo,
                pulseTrainParameters,
                new AmpSettleParameters(),
                chargeRecoveryParameters);

        Map<RHSChannel, ChannelEStimParameters> parametersForChannels_1 = new LinkedHashMap<>();
        for (RHSChannel channel : channels) {
            parametersForChannels_1.put(channel, channelEStimParameters_1);
        }
        EStimParameters eStimParameters_1 = new EStimParameters(parametersForChannels_1);

        Map<RHSChannel, ChannelEStimParameters> parametersForChannels_2 = new LinkedHashMap<>();
        for (RHSChannel channel : channels) {
            parametersForChannels_2.put(channel, channelEStimParameters_2);
        }

        dbUtil.writeEStimObjData(id_1, eStimParameters_1.toXml(), "");
        dbUtil.writeEStimObjData(id_2, channelEStimParameters_2.toXml(),"");
    }
}
