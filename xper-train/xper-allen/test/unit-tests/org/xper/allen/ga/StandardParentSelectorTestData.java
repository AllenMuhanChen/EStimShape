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
    public void testTwoStimWithTwoRepetitions() {
        setUp();

        //actual spikerates calculated via matlab
        //stimId: 2, taskId: 12345, spikeRate: 476.427
        //stimId: 1, taskId:  12346, spikeRate:  471.725

        List<Long> parents = parentSelector.selectParents("3DGA-1");

        assertEquals(2, (long) parents.get(0));
        assertEquals(1, parents.size());

    }


    private void setUp() {
        StandardParentSelector parentSelector = new StandardParentSelector();

        parentSelector.setDbUtil(new ParentSelectorTestMockMultiGaDbUtil());

        IntanSpikeRateSource spikeRateSource = new IntanSpikeRateSource();
        spikeRateSource.setSpikeDatDirectory(ResourceUtil.getResource("IntanSpikeParentSelector-spikeDatDirectory"));
        spikeRateSource.setChannels(Arrays.asList("B-000", "B-031"));
        parentSelector.setSpikeRateSource(spikeRateSource);

        parentSelector.setParentSelectorStrategy(new MaxSpikeRateParentSelectionStrategy());

       this.parentSelector = parentSelector;
    }

}