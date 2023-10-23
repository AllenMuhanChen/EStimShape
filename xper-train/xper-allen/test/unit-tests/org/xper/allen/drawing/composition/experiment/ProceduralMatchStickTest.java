package org.xper.allen.drawing.composition.experiment;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.util.FileUtil;
import org.xper.util.ResourceUtil;

import java.util.Collections;

import static org.junit.Assert.*;
import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class ProceduralMatchStickTest {
    private String testBin;
    private TwobyTwoExperimentMatchStick baseMStick;
    private AllenPNGMaker pngMaker;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

        pngMaker = context.getBean(AllenPNGMaker.class);
        pngMaker.createDrawerWindow();

        baseMStick = new TwobyTwoExperimentMatchStick();
        baseMStick.setProperties(8);
        baseMStick.genMatchStickRand();
    }

    @Test
    public void test_msticks(){
        for (int i = 0; i < 2; i++) {
            generateSet(i);
        }
    }

    private void generateSet(long setId) {
        drawPng(baseMStick, setId, 1L);
        ProceduralMatchStick sampleMStick = new ProceduralMatchStick();
        sampleMStick.setProperties(8);
        sampleMStick.genMatchStickFromDrivingComponent(baseMStick, 1);
        drawPng(sampleMStick, setId, 2L);

        ProceduralMatchStick distractor1 = new ProceduralMatchStick();
        distractor1.setProperties(8);
        distractor1.genNewDrivingComponentMatchStick(sampleMStick, 1, 0.5);
        drawPng(distractor1, setId, 3L);

        ProceduralMatchStick distractor2 = new ProceduralMatchStick();
        distractor2.setProperties(8);
        distractor2.genNewDrivingComponentMatchStick(sampleMStick, 1, 0.5);
        drawPng(distractor2, setId, 4L);
    }

    private void drawPng(ExperimentMatchStick matchStick, long setId, long id) {
//        pngMaker = new AllenPNGMaker(500, 500);
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(matchStick);
        spec.writeInfo2File(testBin + "/" + setId + "_" + id, true);
        pngMaker.createAndSavePNG(matchStick, setId, Collections.singletonList(Long.toString(id)), testBin);
    }
}