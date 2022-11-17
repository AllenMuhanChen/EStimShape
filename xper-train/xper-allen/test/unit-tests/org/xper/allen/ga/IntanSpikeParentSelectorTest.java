package org.xper.allen.ga;

import org.junit.Test;

import java.util.List;

import static org.junit.Assert.*;

public class IntanSpikeParentSelectorTest {

    @Test
    public void test() {
        IntanSpikeParentSelector parentSelector = new IntanSpikeParentSelector();

        List<String> channels;
        List<Long> parents = parentSelector.select(channels);




    }
}