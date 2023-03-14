package org.xper.allen.ga;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.LinkedList;

import static org.junit.Assert.assertEquals;

public class CanopyWidthSourceTest {

    private CanopyWidthSource canopyWidthSource;

    @Before
    public void setUp() throws Exception {
        canopyWidthSource = new CanopyWidthSource();

        canopyWidthSource.setDbUtil(new CanopyWidthSourceTestDbUtil());
        canopyWidthSource.setMaxResponseSource(new MaxResponseSource() {
            @Override
            public double getMaxResponse(String gaName) {
                return 42;
            }
        });

        canopyWidthSource.setSpikeRateSource(new CanopyWidthSourceTestSpikeRateSource());
    }

    @Test
    public void calculates_canopy_width_correctly() {
        //0.8 * 42 = 33.6
        //SpikeRate is set equal to stimId in this test, so the only stimuli that are above this threshold are
        //41L and 42L
        Integer expectedWidth = 2;
        Integer actualWidth = canopyWidthSource.getCanopyWidth(1L);

        assertEquals(expectedWidth, actualWidth);
    }

    @Test
    public void calculates_identical_canopy_widths_from_stims_from_same_tree(){
        Integer expectedWidth = 2;
        Integer actualWidth = canopyWidthSource.getCanopyWidth(21L);
        assertEquals(expectedWidth, actualWidth);

        actualWidth = canopyWidthSource.getCanopyWidth(22L);
        assertEquals(expectedWidth, actualWidth);

        actualWidth = canopyWidthSource.getCanopyWidth(31L);
        assertEquals(expectedWidth, actualWidth);

        actualWidth = canopyWidthSource.getCanopyWidth(32L);
        assertEquals(expectedWidth, actualWidth);
    }

    /**
     * For testing purposes, we create a simple tree
     */
    private static class CanopyWidthSourceTestDbUtil extends MultiGaDbUtil {

        @Override
        public StimGaInfo readStimGaInfo(Long stimId){
            StimGaInfo stimGaInfo = new StimGaInfo();
            Branch<Long> tree  = new Branch<>(1L);
            tree.addChild(new Branch<Long>(21L));
            tree.addChild(new Branch<Long>(22L));
            tree.addChildTo(22L, new Branch<>(31L));
            tree.addChildTo(22L, new Branch<>(32L));
            tree.addChildTo(31L, new Branch<>(41L));
            tree.addChildTo(32L, new Branch<>(42L));

            stimGaInfo.setTreeSpec(tree.toXml());
            return stimGaInfo;
        }
    }

    /**
     * For testing purposes, the spike rate is set equal to the stimId
     */
    public static class CanopyWidthSourceTestSpikeRateSource implements SpikeRateSource {
        @Override
        public Double getSpikeRate(Long taskId) {
            return taskId.doubleValue();
        }
    }
}