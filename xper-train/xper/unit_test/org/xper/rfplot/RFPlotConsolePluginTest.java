package org.xper.rfplot;

import org.junit.BeforeClass;
import org.junit.Ignore;
import org.junit.Test;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.gui.RFPlotConsolePlugin;

import java.util.HashMap;
import java.util.LinkedHashMap;

import static org.junit.Assert.assertEquals;

public class RFPlotConsolePluginTest {

    private static RFPlotConsolePlugin plugin;
    private static MockRFPlotTaskDataSourceClient client;
    private static LinkedHashMap<String, RFPlotDrawable> rfObjectMap;

    @BeforeClass
    public static void setUp(){
        client = new MockRFPlotTaskDataSourceClient();

        rfObjectMap = new LinkedHashMap<>();
        rfObjectMap.put(RFPlotGaborObject.class.getName(), new RFPlotGaborObject());

        plugin = new RFPlotConsolePlugin();
        plugin.setClient(client);
        plugin.setRfObjectMap(rfObjectMap);

    }

    @Test
    public void start(){
        plugin.startPlugin();
    }

    @Ignore
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

    @Ignore
    @Test
    public void mouse_move_changes_location(){
        plugin.handleMouseMove(50,50);

        String xfm = client.getMockXfm();
        RFPlotXfmSpec spec = RFPlotXfmSpec.fromXml(xfm);
        Coordinates2D actualCoords = spec.getTranslation();
        Coordinates2D expectedCoords = new Coordinates2D(50,50);

        assertEquals(expectedCoords, actualCoords);
    }
}
