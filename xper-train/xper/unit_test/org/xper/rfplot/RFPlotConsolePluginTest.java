package org.xper.rfplot;

import org.junit.BeforeClass;
import org.junit.Test;
import org.xper.rfplot.gui.RFPlotConsolePlugin;

import java.util.HashMap;

import static org.junit.Assert.assertEquals;

public class RFPlotConsolePluginTest {

    private static RFPlotConsolePlugin plugin;
    private static MockRFPlotTaskDataSourceClient client;
    private static HashMap<String, RFPlotDrawable> rfObjectMap;

    @BeforeClass
    public static void setUp(){
        client = new MockRFPlotTaskDataSourceClient();

        rfObjectMap = new HashMap<>();
        rfObjectMap.put(RFPlotGaborObject.class.getName(), new RFPlotGaborObject());

        plugin = new RFPlotConsolePlugin();
        plugin.setClient(client);
        plugin.setRfObjectMap(rfObjectMap);

    }

    @Test
    public void start_plugin_sets_default_stim_spec_and_xfm(){
        plugin.startPlugin();

        String actualStimSpec = client.getMockStim();
        String expectedStimSpec = new RFPlotGaborObject().getSpec();

        String actualXfmSpec = client.getMockXfm();
        String expectedXfmSpec = new RFPlotXfmSpec().fromXml(null).toXml();

        assertEquals(expectedStimSpec, actualStimSpec);
        assertEquals(expectedXfmSpec, actualXfmSpec);
    }
}
