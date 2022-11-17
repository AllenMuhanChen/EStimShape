package org.xper.allen.ga;

import org.junit.Test;
import org.xper.allen.util.TestMultiGaDbUtil;
import org.xper.intan.read.SpikeReader;
import org.xper.util.ResourceUtil;

import javax.annotation.Resource;
import java.util.LinkedList;
import java.util.List;

import static org.junit.Assert.*;

public class IntanSpikeParentSelectorTest {

    private IntanSpikeParentSelector parentSelector;

    @Test
    public void test12345HigherSpikeRate() {
        setUp();

        //actual spikerates calculated via matlab
        //12345: 476.427
        //12346" 471.725

        List<String> channels = new LinkedList<>();
        channels.add("B-000");
        channels.add("B-031");

        List<Long> parents = parentSelector.selectParents(channels);

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

        List<Long> parents = parentSelector.selectParents(channels);

        assertEquals(12346, (long) parents.get(0));
        assertEquals(1, parents.size());
    }

    private void setUp() {
        IntanSpikeParentSelector parentSelector = new IntanSpikeParentSelector();
        parentSelector.setGaName("3DGA-1");
        parentSelector.setDbUtil(new TestMultiGaDbUtil());
        parentSelector.setSpikeDatDirectory(ResourceUtil.getResource("IntanSpikeParentSelector-spikeDatDirectory"));


       this.parentSelector = parentSelector;
    }

}