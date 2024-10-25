package org.xper.allen.pga.alexnet;

import org.junit.Before;
import org.junit.Test;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

import java.util.ArrayList;

public class AlexNetDrawingManagerTest {

    private AlexNetDrawingManager alexNetDrawingManager;

    @Before
    public void setUp() throws Exception {
        alexNetDrawingManager = new AlexNetDrawingManager();
        alexNetDrawingManager.setGeneratorDPI(68.31);
    }

    @Test
    public void testCalculateMmForPixels(){
        System.out.println((alexNetDrawingManager.calculateMmForPixels(227)));
    }

    @Test
    public void testDrawing(){
        alexNetDrawingManager.createDrawerWindow();
        AlexNetGAMatchStick mStick = new AlexNetGAMatchStick(new float[]{0.0f, 354.0f, 354.0f, 1.0f},
                new RGBColor(1.0, 1.0, 1.0),
                new Coordinates2D(0,0),
                10,
                "2D", 1.0);
        mStick.genMatchStickRand();

        alexNetDrawingManager.createAndSavePNG(mStick, 1L, new ArrayList<>(), "/home/r2_allen/git/EStimShape/xper-train/xper-allen/test/test-resources/testBin");
    }
}