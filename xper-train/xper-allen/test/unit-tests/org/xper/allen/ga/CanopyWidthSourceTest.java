package org.xper.allen.ga;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.util.MultiGaDbUtil;

public class CanopyWidthSourceTest {

    private CanopyWidthSource canopyWidthSource;

    @Before
    public void setUp() throws Exception {
        canopyWidthSource = new CanopyWidthSource();

        canopyWidthSource.setDbUtil(new CanopyWidthSourceTestDbUtil());
        canopyWidthSource.setMaxResponseSource(new MaxResponseSource() {
            @Override
            public double getMaxResponse() {
                return 1.0;
            }
        });
    }

    @Test
    public void getCanopyWidth() {

    }

    private static class CanopyWidthSourceTestDbUtil extends MultiGaDbUtil {

        @Override
        public StimGaInfo readStimGaInfo(Long stimId){
            StimGaInfo stimGaInfo = new StimGaInfo();
            Branch tree  = new Branch(1L);
            tree.addChild(new Branch(21L));
            tree.addChild(new Branch(22L));
            tree.addChildTo(22L, new Branch(31L));
            tree.addChildTo(22L, new Branch(32L));

            stimGaInfo.setTreeSpec(tree.toXml());
            return stimGaInfo;
        }
    }
}