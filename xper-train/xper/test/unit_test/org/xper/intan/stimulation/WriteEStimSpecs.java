package org.xper.intan.stimulation;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.XperConfig;
import org.xper.allen.util.AllenDbUtil;
import org.xper.time.TimeUtil;
import org.xper.util.FileUtil;

import java.util.*;

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
    public void write_260107_0_estim(){
        long id = 1L;
        RHSChannel channel = RHSChannel.A026;
        StimulationShape shape = StimulationShape.BiphasicWithInterphaseDelay;
        double d1 = 200.0;
        double d2 = 200.0;
        double dp = 100.0;
        double a1 = 2.5;
        double a2 = 2.5;
        WaveformParameters waveform = new WaveformParameters(
                shape,
                StimulationPolarity.NegativeFirst,
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

        ChannelEStimParameters channelEStimParameters = new ChannelEStimParameters(
                waveform,
                pulseTrainParameters);

        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = new LinkedHashMap<>();
        parametersForChannels.put(channel, channelEStimParameters);

        EStimParameters eStimParameters = new EStimParameters(parametersForChannels);
        dbUtil.writeEStimObjData(id, eStimParameters.toXml(), "");
    }


    @Test
    public void write_anodic_and_cathodic_first_mix() throws Exception {
        long id_1 = 1L;
        long id_2 = 2L;

        List<RHSChannel> channels = new ArrayList<>();
        channels.add(RHSChannel.A031);
        channels.add(RHSChannel.A027);
        channels.add(RHSChannel.A004);
        channels.add(RHSChannel.A028);
        channels.add(RHSChannel.A001);
        channels.add(RHSChannel.A003);
        channels.add(RHSChannel.A029);
        channels.add(RHSChannel.A002);
        channels.add(RHSChannel.A030);


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

        EStimParameters eStimParameters_2 = new EStimParameters(parametersForChannels_2);

        dbUtil.writeEStimObjData(id_1, eStimParameters_1.toXml(), "");
        dbUtil.writeEStimObjData(id_2, eStimParameters_2.toXml(),"");
    }


    @Test
    public void write_251231_0_estim(){
        long id = 1L;
        RHSChannel channel = RHSChannel.A018;
        StimulationShape shape = StimulationShape.BiphasicWithInterphaseDelay;
        double d1 = 200.0;
        double d2 = 200.0;
        double dp = 100.0;
        double a1 = 2.5;
        double a2 = 2.5;
        WaveformParameters waveform = new WaveformParameters(
                shape,
                StimulationPolarity.NegativeFirst,
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

        ChannelEStimParameters channelEStimParameters = new ChannelEStimParameters(
                waveform,
                pulseTrainParameters);

        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = new LinkedHashMap<>();
        parametersForChannels.put(channel, channelEStimParameters);

        EStimParameters eStimParameters = new EStimParameters(parametersForChannels);
        dbUtil.writeEStimObjData(id, eStimParameters.toXml(), "");
    }


    @Test
    public void write_251226_0_estim(){
        long id = 1L;
        RHSChannel channel = RHSChannel.A025;
        StimulationShape shape = StimulationShape.BiphasicWithInterphaseDelay;
        double d1 = 200.0;
        double d2 = 200.0;
        double dp = 100.0;
        double a1 = 2.5;
        double a2 = 2.5;
        WaveformParameters waveform = new WaveformParameters(
                shape,
                StimulationPolarity.NegativeFirst,
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

        ChannelEStimParameters channelEStimParameters = new ChannelEStimParameters(
                waveform,
                pulseTrainParameters);

        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = new LinkedHashMap<>();
        parametersForChannels.put(channel, channelEStimParameters);

        EStimParameters eStimParameters = new EStimParameters(parametersForChannels);
        dbUtil.writeEStimObjData(id, eStimParameters.toXml(), "");
    }


    @Test
    public void write_260108_0_estim(){
        // for gen_id 9-16
        long id = 1L;
        List<RHSChannel> channels = new  ArrayList<>();
        channels.add(RHSChannel.A011);
        channels.add(RHSChannel.A021);
        StimulationShape shape = StimulationShape.BiphasicWithInterphaseDelay;
        double d1 = 200.0;
        double d2 = 200.0;
        double dp = 100.0;
        double a1 = 2.5;
        double a2 = 2.5;
        WaveformParameters waveform = new WaveformParameters(
                shape,
                StimulationPolarity.NegativeFirst,
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

        ChannelEStimParameters channelEStimParameters = new ChannelEStimParameters(
                waveform,
                pulseTrainParameters,
                new AmpSettleParameters(),
                chargeRecoveryParameters
                );

        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = new LinkedHashMap<>();
        for  (RHSChannel channel : channels) {
            parametersForChannels.put(channel, channelEStimParameters);
        }


        EStimParameters eStimParameters = new EStimParameters(parametersForChannels);
        dbUtil.writeEStimObjData(id, eStimParameters.toXml(), "");
    }

}
