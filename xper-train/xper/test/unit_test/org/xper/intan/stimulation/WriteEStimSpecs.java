package org.xper.intan.stimulation;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.XperConfig;
import org.xper.allen.util.AllenDbUtil;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

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
    public void test() throws Exception {
        RHSChannel channel = RHSChannel.A024;
        List<RHSChannel> channels = new ArrayList<>();
        channels.add(channel);
        channels.add(RHSChannel.A000);
        channels.add(RHSChannel.A006);
        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = new LinkedHashMap<>();
        WaveformParameters waveformOne = new WaveformParameters(
                StimulationShape.Biphasic,
                StimulationPolarity.NegativeFirst,
                200.0,
                200.0,
                100.0,
                2.5,
                2.5
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
                waveformOne,
                pulseTrainParameters,
                new AmpSettleParameters(),
                chargeRecoveryParameters);


        parametersForChannels.put(channels.get(0), channelEStimParameters);
        parametersForChannels.put(channels.get(1), channelEStimParameters);
        parametersForChannels.put(channels.get(2), channelEStimParameters);
        EStimParameters eStimParameters = new EStimParameters(parametersForChannels);

        dbUtil.writeEStimObjData(4L, eStimParameters.toXml(), "");
    }
}
