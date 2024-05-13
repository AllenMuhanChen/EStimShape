package org.xper.allen.drawing.composition.experiment;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.AllenDrawingManager;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.TestDrawingWindow;
import org.xper.util.FileUtil;
import org.xper.util.ResourceUtil;

import java.awt.*;
import java.util.Collections;

import static org.junit.Assert.*;
import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class EStimShapeProceduralMatchStickTest {
    private TestMatchStickDrawer testMatchStickDrawer;
    private String testBin;
    private ProceduralMatchStick baseMStick;
    private AllenPNGMaker pngMaker;
    private TestDrawingWindow window;
    private AllenDrawingManager drawingManager;
    private int numNoiseFrames;
    private EStimShapeProceduralMatchStick testMStick;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

//        pngMaker = context.getBean(AllenPNGMaker.class);
//        pngMaker.createDrawerWindow();
//        drawingManager = pngMaker.window;
        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup(500, 500);

        baseMStick = new ProceduralMatchStick();
        baseMStick.setProperties(4, "SHADE");
        baseMStick.setStimColor(new Color(255,255,255));
        baseMStick.genMatchStickRand();
        baseMStick.setMaxAttempts(-1);


    }

    @Test
    public void test_completely_in_RF(){
//        pngMaker.createDrawerWindow();

        ReceptiveField receptiveField = new ReceptiveField() {
            double h = 5;
            double k = 5;
            double r = 10;

            {
                for (int i = 0; i < 100; i++) {
                    double angle = 2 * Math.PI * i / 100;
                    outline.add(new Coordinates2D(h + r * Math.cos(angle), k + r * Math.sin(angle)));
                }
            }
            @Override
            public boolean isInRF(double x, double y) {
                return (x- h)*(x- h) + (y- k)*(y- k) < r * r;
            }
        };
        EStimShapeProceduralMatchStick mStick = new EStimShapeProceduralMatchStick(RFStrategy.COMPLETELY_INSIDE, receptiveField);

        mStick.setProperties(4, "SHADE");

        mStick.genMatchStickFromComponentInNoise(baseMStick, 1, 3);
        testMatchStickDrawer.draw(new Drawable() {
            @Override
            public void draw() {
                mStick.drawCompMap();
            }
        });


    }

    public void drawPng(ProceduralMatchStick matchStick, String label) {
//        pngMaker = new AllenPNGMaker(500, 500);
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(matchStick, true);
        spec.writeInfo2File(testBin + "/" + label, true);
        pngMaker.createAndSavePNG(matchStick, 1L, Collections.singletonList(Long.toString(1)), testBin);
    }
}