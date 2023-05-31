package org.xper.allen.drawing.composition.experiment;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.alden.drawing.drawables.PNGmaker;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.util.DPIUtil;
import org.xper.drawing.stick.MatchStick;
import org.xper.util.FileUtil;
import org.xper.util.ResourceUtil;

import java.util.Arrays;
import java.util.Collections;

import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class ExperimentMatchStickTest {

    private String testBin;
    private ExperimentMatchStick baseMStick;
    private AllenPNGMaker pngMaker;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

        pngMaker = context.getBean(AllenPNGMaker.class);
        pngMaker.createDrawerWindow();

        baseMStick = new ExperimentMatchStick();
        baseMStick.setProperties(8);
        baseMStick.genMatchStickRand();


        drawPng(baseMStick, 1L);

    }

    @Test
    public void test_msticks() {
        ExperimentMatchStick firstMStick = new ExperimentMatchStick();
        firstMStick.setProperties(8);
        firstMStick.genFirstMatchStick(baseMStick, 1);
        drawPng(firstMStick, 2L);

        ExperimentMatchStick secondMStick = new ExperimentMatchStick();
        secondMStick.setProperties(8);
        secondMStick.genSecondMatchStick(firstMStick, 1);
        drawPng(secondMStick, 3L);

        ExperimentMatchStick thirdMStick = new ExperimentMatchStick();
        thirdMStick.setProperties(8);
        thirdMStick.genThirdMatchStick(firstMStick, 1, 0.5);
        drawPng(thirdMStick, 4L);

        ExperimentMatchStick fourthMStick = new ExperimentMatchStick();
        fourthMStick.setProperties(8);
        fourthMStick.genFourthMatchStick(secondMStick, 1, thirdMStick);
        drawPng(fourthMStick, 5L);

    }

    private void drawPng(ExperimentMatchStick matchStick, long id) {
//        pngMaker = new AllenPNGMaker(500, 500);
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(matchStick);
        spec.writeInfo2File(testBin + "/" + 1 + "_" + id, true);
        pngMaker.createAndSavePNG(matchStick, 1L, Collections.singletonList(Long.toString(id)), testBin);
    }

    @After
    public void tearDown() throws Exception {
        pngMaker.close();
    }
}