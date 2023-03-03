package org.xper.allen.drawing.composition.ga;

import org.junit.Before;
import org.junit.Test;
import org.xper.alden.drawing.drawables.PNGmaker;
import org.xper.drawing.stick.MatchStick;
import org.xper.util.ResourceUtil;

import java.util.Arrays;

import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class GrowingMatchStickTest {

    private GrowingMatchStick gms;
    private String testBin;

    @Before
    public void setUp() throws Exception {
        initXperLibs();

        testBin = ResourceUtil.getResource("testBin");

        gms = new GrowingMatchStick();
        String test_stick_path = ResourceUtil.getResource("test-stick.xml");
        gms.genMatchStickFromFile(test_stick_path);

    }

    @Test
    public void mutate() {
        drawPng(gms, 1L);
//        gms.mutate(0);
//        drawPng(gms, 2L);
    }

    private void drawPng(MatchStick matchStick, long id) {
        PNGmaker pngMaker = new PNGmaker(500, 500);
        pngMaker.createAndSavePNGsfromObjs(Arrays.asList(matchStick), Arrays.asList(new Long[]{id}), testBin);
    }
}