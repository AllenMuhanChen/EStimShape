package org.xper.allen.drawing.composition.experiment;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.util.FileUtil;
import org.xper.util.ResourceUtil;

import java.util.Collections;

import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class TwobyTwoProceduralMatchStickTest {

    private String testBin;
    private TwobyTwoProceduralMatchStick baseMStick;
    private AllenPNGMaker pngMaker;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

        pngMaker = context.getBean(AllenPNGMaker.class);
        pngMaker.createDrawerWindow();

        baseMStick = new TwobyTwoProceduralMatchStick();
        baseMStick.setProperties(8, "SHADE");
        baseMStick.genMatchStickRand();


        drawPng(baseMStick, 1L);

    }

    @Test
    public void test_msticks() {
        TwobyTwoProceduralMatchStick firstMStick = new TwobyTwoProceduralMatchStick();
        firstMStick.setProperties(8, "SHADE");
        firstMStick.genMatchStickFromComponent(baseMStick, 1, 0);
        drawPng(firstMStick, 2L);

        TwobyTwoProceduralMatchStick secondMStick = new TwobyTwoProceduralMatchStick();
        secondMStick.setProperties(8, "SHADE");
        secondMStick.genNewBaseMatchStick(firstMStick, 1);
        drawPng(secondMStick, 3L);

        TwobyTwoProceduralMatchStick thirdMStick = new TwobyTwoProceduralMatchStick();
        thirdMStick.setProperties(8, "SHADE");
        thirdMStick.genNewDrivingComponentMatchStick(firstMStick, 0.5, 0.5);
        drawPng(thirdMStick, 4L);

        TwobyTwoProceduralMatchStick fourthMStick = new TwobyTwoProceduralMatchStick();
        fourthMStick.setProperties(8, "SHADE");
        fourthMStick.genFourthMatchStick(secondMStick, 1, thirdMStick);
        drawPng(fourthMStick, 5L);

    }

    private void drawPng(TwobyTwoProceduralMatchStick matchStick, long id) {
//        pngMaker = new AllenPNGMaker(500, 500);
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(matchStick, true);
        spec.writeInfo2File(testBin + "/" + 1 + "_" + id, true);
        pngMaker.createAndSavePNG(matchStick, 1L, Collections.singletonList(Long.toString(id)), testBin);
    }

    @After
    public void tearDown() throws Exception {
        pngMaker.close();
    }
}