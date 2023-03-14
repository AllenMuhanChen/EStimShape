package org.xper.allen.ga;

import org.junit.Before;
import org.junit.Test;
import org.xper.util.ResourceUtil;

import java.util.LinkedList;
import java.util.List;

import static org.junit.Assert.*;

public class IntanAverageSpikeRateSourceTest {

    private IntanAverageSpikeRateSource spikeRateSource;

    @Before
    public void setUp() throws Exception {
        spikeRateSource = new IntanAverageSpikeRateSource();
        spikeRateSource.setSpikeDatDirectory((ResourceUtil.getResource("IntanSpikeParentSelector-spikeDatDirectory")));
    }

    @Test
    public void test_read() {
        List<String> channels = new LinkedList<>();
        channels.add("B-000");
        channels.add("B-031");

        spikeRateSource.setChannels(channels);

        Double spikeRate = spikeRateSource.getSpikeRate(12345L);

        assertEquals(238.273, spikeRate, 0.001);

    }
}