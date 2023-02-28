package org.xper.allen.ga;

import org.junit.Test;
import org.xper.allen.util.ParentSelectorTestMockMultiGaDbUtil;
import org.xper.util.ResourceUtil;

import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

import static org.junit.Assert.*;

public class StandardParentSelectorTestData {

    private StandardParentSelector parentSelector;

    @Test
    public void test12345HigherSpikeRate() {
        setUp();

        //actual spikerates calculated via matlab
        //12345: 476.427
        //12346" 471.725


        List<Long> parents = parentSelector.selectParents("3DGA-1");

        assertEquals(12345, (long) parents.get(0));
        assertEquals(1, parents.size());

    }

    @Test
    public void test12346HigherSpikeRate(){
        setUp();

        //actual spikerates calculated via matlab
        //12345: 391.70
        //12346: 393.71

        List<String> channels = new LinkedList<>();
        channels.add("B-000");
        channels.add("B-015");

        List<Long> parents = parentSelector.selectParents("3DGA-1");

        assertEquals(12346, (long) parents.get(0));
        assertEquals(1, parents.size());
    }

    private void setUp() {
        StandardParentSelector parentSelector = new StandardParentSelector();

        parentSelector.setDbUtil(new ParentSelectorTestMockMultiGaDbUtil());

        IntanSpikeRateSource spikeRateSource = new IntanSpikeRateSource();
        spikeRateSource.setSpikeDatDirectory(ResourceUtil.getResource("IntanSpikeParentSelector-spikeDatDirectory"));
        spikeRateSource.setChannels(Arrays.asList("B-000", "B-031"));
        parentSelector.setSpikeRateSource(spikeRateSource);

        parentSelector.setParentSelectorStrategy(new MaxSpikeRateParentSelectorStrategy());

       this.parentSelector = parentSelector;
    }

}