package org.xper.intan.stimulation;

import org.junit.Before;
import org.junit.Test;
import org.xper.XperConfig;
import org.xper.intan.IntanClient;
import org.xper.intan.Parameter;
import org.xper.intan.stimulation.IntanStimulationController;
import org.xper.intan.stimulation.RHSChannel;
import org.xper.time.DefaultTimeUtil;

import java.util.*;

import static org.junit.Assert.*;

public class IntanStimulationControllerTest {

    private IntanClient intanClient;
    private IntanStimulationController controller;

    @Before
    public void setUp() throws Exception {
        List<String> libs = new ArrayList<String>();
        libs.add("xper");
        new XperConfig("", libs);

        intanClient = new IntanClient();
        intanClient.setTimeUtil(new DefaultTimeUtil());
        intanClient.setHost("172.30.9.78");
        intanClient.setPort(5000);


        controller = new IntanStimulationController();
        controller.setIntanClient(intanClient);
        controller.setDefaultParameters(defaultParameters());

        controller.connect();
        assertTrue(controller.getIntanClient().get("b-000.maintainampsettle").equals("True"));
    }

    @Test
    public void tcpNameForIntanChannel() {
        String channelString = IntanStimulationController.tcpNameForIntanChannel(RHSChannel.A000);
        assertEquals("a-000", channelString);
    }

    @Test
    public void testStimulationSetup(){
        Map<RHSChannel, Collection<Parameter>> parametersForChannels = new LinkedHashMap<>();
        parametersForChannels.put(RHSChannel.B000, Arrays.asList(new Parameter<String>("Polarity", "NegativeFirst")));

        controller.setupStimulationFor(parametersForChannels);

        String stim_enabled = controller.getIntanClient().get("b-000.stimenabled");
        assertTrue(stim_enabled.equals("True"));

        assertTrue(controller.getIntanClient().get("b-000.polarity").equals("NegativeFirst"));
    }

    private List<Parameter> defaultParameters(){
        List<Parameter> parameters = new LinkedList<>();
        parameters.add(new Parameter("MaintainAmpSettle", "True"));


        return parameters;
  }
}