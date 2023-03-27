package org.xper.allen.drawing.composition.morph;

import org.junit.Before;
import org.junit.Test;
import org.xper.alden.drawing.drawables.PNGmaker;
import org.xper.drawing.stick.MatchStick;
import org.xper.util.ResourceUtil;
import org.xper.util.ThreadUtil;

import java.util.Arrays;

import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class GrowingMatchStickTest {

    private MorphedMatchStick parentMStick;
    private String testBin;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        parentMStick = new MorphedMatchStick();
        parentMStick.setProperties(30);
//        String test_stick_path = ResourceUtil.getResource("test-stick.xml");
//        parentMStick.genMatchStickFromFile(test_stick_path);
        parentMStick.genMatchStickRand();


        drawPng(parentMStick, 1L);
    }

    @Test
    public void genRegimeOneMatchStick() {
        GrowingMatchStick growingMatchStick = new GrowingMatchStick();
        growingMatchStick.setProperties(30.0);
        growingMatchStick.genGrowingMatchStick(parentMStick, 0.2);
        ThreadUtil.sleep(500);
        drawPng(growingMatchStick, 2L);
    }

    private void drawPng(MatchStick matchStick, long id) {
        PNGmaker pngMaker = new PNGmaker(500, 500);
        pngMaker.createAndSavePNGsfromObjs(Arrays.asList(matchStick), Arrays.asList(new Long[]{id}), testBin);
    }
}