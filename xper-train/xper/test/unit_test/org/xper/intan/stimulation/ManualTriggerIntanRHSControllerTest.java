package org.xper.intan.stimulation;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;
import org.xper.XperConfig;
import org.xper.intan.IntanClient;
import org.xper.time.DefaultTimeUtil;
import org.xper.util.ThreadUtil;

import java.util.*;

import static org.junit.Assert.*;

public class ManualTriggerIntanRHSControllerTest {

    private IntanClient intanClient;
    private ManualTriggerIntanRHS controller;

    @Before
    public void setUp() throws Exception {
        List<String> libs = new ArrayList<String>();
        libs.add("xper");
        new XperConfig("", libs);

        intanClient = new IntanClient();
        intanClient.setTimeUtil(new DefaultTimeUtil());
        intanClient.setHost("172.30.9.78");
        intanClient.setPort(5000);


        controller = new ManualTriggerIntanRHS();
        controller.setIntanClient(intanClient);
        controller.setDefaultParameters(defaultParameters());

        controller.connect();
//        assertTrue(controller.getIntanClient().get("b-000.maintainampsettle").equals("True"));
    }

    @Ignore
    @Test
    public void enumToStringTest(){
        PulseRepetition pulseRepetition = PulseRepetition.PulseTrain;
        String pulseRepetitionString = pulseRepetition.toString();
        assertEquals("PulseTrain", pulseRepetitionString);
    }

    @Test
    public void tcpNameForIntanChannel() {
        String channelString = ManualTriggerIntanRHS.tcpNameForIntanChannel(RHSChannel.A000);
        assertEquals("a-000", channelString);
    }

    @Test
    public void testStimulationSetup(){
        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = new LinkedHashMap<>();
        WaveformParameters waveformParameters = new WaveformParameters(
                StimulationShape.Biphasic,
                StimulationPolarity.NegativeFirst,
                5000.0,
                5000.0,
                1000.0,
                50.0,
                50.0
        );

        PulseTrainParameters pulseTrainParameters = new PulseTrainParameters(
                PulseRepetition.SinglePulse,
                1,
                0.0,
                0.0
        );

        ChannelEStimParameters channelEStimParameters = new ChannelEStimParameters(waveformParameters, pulseTrainParameters);
        parametersForChannels.put(RHSChannel.B000, channelEStimParameters);
        EStimParameters eStimParameters = new EStimParameters(parametersForChannels);

        controller.setupStimulationFor(eStimParameters);

        String stim_enabled = controller.getIntanClient().get("b-000.stimenabled");
        assertTrue(stim_enabled.equals("True"));

        assertTrue(controller.getIntanClient().get("b-000.polarity").equals("NegativeFirst"));
    }

    @Test
    public void testPulse(){
        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = new LinkedHashMap<>();
        WaveformParameters waveformParameters = new WaveformParameters(
                StimulationShape.Biphasic,
                StimulationPolarity.NegativeFirst,
                5000.0,
                5000.0,
                1000.0,
                50.0,
                50.0
        );

        PulseTrainParameters pulseTrainParameters = new PulseTrainParameters(
                PulseRepetition.SinglePulse,
                1,
                10.0,
                1.0
        );

        ChannelEStimParameters channelEStimParameters = new ChannelEStimParameters(waveformParameters, pulseTrainParameters);
        parametersForChannels.put(RHSChannel.B025, channelEStimParameters);
        EStimParameters eStimParameters = new EStimParameters(parametersForChannels);

        controller.setupStimulationFor(eStimParameters);
        controller.stopRecording();


        for(int i = 0; i < 30; i++) {
            controller.trigger();
            ThreadUtil.sleep(1000);
        }
    }

    private List<Parameter<Object>> defaultParameters(){
        List<Parameter<Object>> parameters = new LinkedList<>();
        parameters.add(new Parameter<>("MaintainAmpSettle", "True"));


        return parameters;
  }
}