package org.xper.allen.ga;

import org.junit.Before;
import org.junit.Test;
import org.xper.util.ResourceUtil;

import java.util.LinkedList;
import java.util.List;

import static org.junit.Assert.*;

public class IntanSpikeRateSourceTest {

    private IntanSpikeRateSource spikeRateSource;

    @Before
    public void setUp() throws Exception {
        spikeRateSource = new IntanSpikeRateSource();
        spikeRateSource.setSpikeDatDirectory((ResourceUtil.getResource("IntanSpikeParentSelector-spikeDatDirectory")));
    }

    @Test
    public void test_read() {
        List<String> channels = new LinkedList<>();
        channels.add("B-000");
        channels.add("B-031");

        spikeRateSource.setChannels(channels);

        List<Double> spikeRates = spikeRateSource.getSpikeRates(12345L);

        assertEquals(2, spikeRates.size());
        assertEquals(205.574, spikeRates.get(0), 0.001);
        assertEquals(270.973, spikeRates.get(1), 0.001);
    }
}