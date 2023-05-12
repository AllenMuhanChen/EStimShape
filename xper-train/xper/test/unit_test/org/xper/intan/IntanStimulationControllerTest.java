package org.xper.intan;

import org.junit.Before;
import org.junit.Test;
import org.xper.time.DefaultTimeUtil;

import java.util.*;

import static org.junit.Assert.*;

public class IntanStimulationControllerTest {

    private IntanClient intanClient;
    private IntanStimulationController controller;

    @Before
    public void setUp() throws Exception {
        intanClient = new IntanClient();
        intanClient.setTimeUtil(new DefaultTimeUtil());
        intanClient.setHost("172.30.9.78");
        intanClient.setPort(5000);


        controller = new IntanStimulationController();
        controller.setIntanClient(intanClient);
        controller.setDefaultParameters(defaultParameters());

        controller.connect();
    }

    @Test
    public void tcpNameForIntanChannel() {
        String channelString = IntanStimulationController.tcpNameForIntanChannel(RHSChannel.A000);
        assertEquals("a-000", channelString);
    }

    @Test
    public void testStimulationSetup(){
        Map<RHSChannel, Parameter> parametersForChannels = new LinkedHashMap<>();
        parametersForChannels.put(RHSChannel.B000, new Parameter("Polarity", "NegativeFirst"));
//        controller.setupStimulationFor();
    }

    private List<Parameter> defaultParameters(){
        List<Parameter> parameters = new LinkedList<>();
        parameters.add(new Parameter("MaintainAmpSettle", "True"));

        return parameters;
  }
}