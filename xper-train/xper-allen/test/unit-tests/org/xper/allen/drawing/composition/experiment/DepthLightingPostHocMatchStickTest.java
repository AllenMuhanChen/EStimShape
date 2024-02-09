package org.xper.allen.drawing.composition.experiment;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;

public class DepthLightingPostHocMatchStickTest {

    private TestMatchStickDrawer drawer;

    @Before
    public void setUp() throws Exception {
        drawer = new TestMatchStickDrawer();
        drawer.setup(190, 190);

    }

    @Test
    public void test() {
        //potential good base mSticks
        //1702588420352043_sample
        //1702588489214206_sample

        String filename = "/home/r2_allen/git/EStimShape/xper-train/stimuli/procedural/specs/1702588489214206_spec.xml";
        DepthLightingPostHocMatchStick baseMStick = new DepthLightingPostHocMatchStick();
        baseMStick.setProperties(12);
        baseMStick.genMatchStickFromFile(filename);

        drawer.drawMStick(baseMStick);

        DepthLightingPostHocMatchStick flippedStick = new DepthLightingPostHocMatchStick();
        flippedStick.setProperties(12);
        int componentId = 1;
        flippedStick.genFlippedMatchStick(baseMStick, componentId);
    }
}