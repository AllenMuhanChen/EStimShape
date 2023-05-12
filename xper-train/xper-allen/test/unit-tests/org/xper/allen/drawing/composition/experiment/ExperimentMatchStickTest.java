package org.xper.allen.drawing.composition.experiment;

import org.junit.Before;
import org.junit.Test;
import org.xper.alden.drawing.drawables.PNGmaker;
import org.xper.drawing.stick.MatchStick;
import org.xper.util.ResourceUtil;

import java.util.Arrays;

import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class ExperimentMatchStickTest {

    private String testBin;
    private ExperimentMatchStick baseMStick;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        baseMStick = new ExperimentMatchStick();
        baseMStick.setProperties(30);
        baseMStick.genMatchStickRand();

        drawPng(baseMStick, 1L);

    }

    @Test
    public void test_msticks() {
        ExperimentMatchStick firstMStick = new ExperimentMatchStick();
        firstMStick.setProperties(30);
        firstMStick.genFirstMatchStick(baseMStick, 1);
        drawPng(firstMStick, 2L);

        ExperimentMatchStick secondMStick = new ExperimentMatchStick();
        secondMStick.setProperties(30);
        secondMStick.genSecondMatchStick(firstMStick, 1);
        drawPng(secondMStick, 3L);

        ExperimentMatchStick thirdMStick = new ExperimentMatchStick();
        thirdMStick.setProperties(30);
        thirdMStick.genThirdMatchStick(firstMStick, 1, 0.5);
        drawPng(thirdMStick, 4L);

        ExperimentMatchStick fourthMStick = new ExperimentMatchStick();
        fourthMStick.setProperties(30);
        fourthMStick.genFourthMatchStick(secondMStick, 1, thirdMStick);
        drawPng(fourthMStick, 5L);

    }

    private void drawPng(MatchStick matchStick, long id) {
        PNGmaker pngMaker = new PNGmaker(500, 500);
        pngMaker.createAndSavePNGsfromObjs(Arrays.asList(matchStick), Arrays.asList(new Long[]{id}), testBin);
    }
}