package org.xper.allen.drawing.composition.experiment;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.util.ThreadUtil;

public class DepthLightingPostHocMatchStickTest {

    public static final int TIME = 1000;
    private TestMatchStickDrawer drawer;
    private String figurePath;

    @Before
    public void setUp() throws Exception {
        drawer = new TestMatchStickDrawer();
        drawer.setup(190, 190);

        figurePath = "/home/r2_allen/git/EStimShape/plots/grant_240209";


    }

    @Test
    public void test_counters() {
        //potential good base mSticks
        //1702588420352043_sample
        //1702588489214206_sample

        String filename = "/home/r2_allen/git/EStimShape/xper-train/stimuli/procedural/specs/1702588489214206_spec.xml";
        DepthLightingPostHocMatchStick baseMStick = new DepthLightingPostHocMatchStick();
        baseMStick.setProperties(12);
        baseMStick.setTextureType("2D");
        baseMStick.genMatchStickFromFile(filename);

        drawer.drawGhost(baseMStick);
        ThreadUtil.sleep(TIME);

        DepthLightingPostHocMatchStick flippedStick = new DepthLightingPostHocMatchStick();
        flippedStick.setProperties(12);
        flippedStick.setTextureType("2D");
        int componentId = 1;
        flippedStick.genFlippedMatchStick(baseMStick, componentId);

//        drawer.clear();
        drawer.drawGhost(flippedStick);
        ThreadUtil.sleep(TIME);
    }

    @Test
    public void test_lighting(){
        float[][] lightPositions = new float[][]{
                {0.0f, 354.0f, 354.0f, 1.0f},
                {0.0f, -354.0f, 354.0f, 1.0f},
                {354.0f, 0.0f, 354.0f, 1.0f},
                {-354.0f, 0.0f, 354.0f, 1.0f},
        };

        String filename = "/home/r2_allen/git/EStimShape/xper-train/stimuli/procedural/specs/1702588489214206_spec.xml";
        DepthLightingPostHocMatchStick baseMStick = new DepthLightingPostHocMatchStick();
        baseMStick.setProperties(12);
        baseMStick.genMatchStickFromFile(filename);
        int index=0;
        for (float[] lightPosition : lightPositions) {
            baseMStick.light_position = lightPosition;
            drawer.clear();
            drawer.drawMStick(baseMStick);
            drawer.saveImage(figurePath + "/original_shape_with_lighting_" + index);
            ThreadUtil.sleep(TIME);
            index++;
        }


        DepthLightingPostHocMatchStick flippedStick = new DepthLightingPostHocMatchStick();
        flippedStick.setProperties(12);
        int componentId = 1;
        flippedStick.genFlippedMatchStick(baseMStick, componentId);

        index=0;
        for (float[] lightPosition : lightPositions) {
            flippedStick.light_position = lightPosition;
            drawer.clear();
            drawer.drawMStick(flippedStick);
            drawer.saveImage(figurePath + "/flipped_shape_with_lighting_" + index);
            ThreadUtil.sleep(TIME);
            index++;
        }
    }
}