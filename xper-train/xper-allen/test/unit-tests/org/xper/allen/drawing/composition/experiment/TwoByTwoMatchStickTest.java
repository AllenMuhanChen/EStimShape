package org.xper.allen.drawing.composition.experiment;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.util.FileUtil;
import org.xper.util.ResourceUtil;

import java.util.Collections;

import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class TwoByTwoMatchStickTest {

    private String testBin;
    private TwoByTwoMatchStick baseMStick;
    private AllenPNGMaker pngMaker;

    public static final ReceptiveField PARTIAL_RF = new ReceptiveField() {
        double h = 20;
        double k = 20;
        double r = 10;

        {
            center = new Coordinates2D(h, k);
            radius = r;
            for (int i = 0; i < 100; i++) {
                double angle = 2 * Math.PI * i / 100;
                outline.add(new Coordinates2D(h + r * Math.cos(angle), k + r * Math.sin(angle)));
            }
        }

        @Override
        public boolean isInRF(double x, double y) {
            return (x - h) * (x - h) + (y - k) * (y - k) < r * r;
        }
    };

    @Before
    public void setUp() throws Exception {


        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

        pngMaker = context.getBean(AllenPNGMaker.class);
        pngMaker.createDrawerWindow();


        baseMStick = new TwoByTwoMatchStick(new GaussianNoiseMapper());
        baseMStick.setProperties(8, "SHADE");
        baseMStick.genMatchStickRand();


        drawPng(baseMStick, 1L);

    }

    @Test
    public void test_msticks() {
        TwoByTwoMatchStick firstMStick = new TwoByTwoMatchStick(new GaussianNoiseMapper());
        firstMStick.setProperties(40, "SHADE");
        firstMStick.genMatchStickFromComponent(baseMStick, 1, 2, firstMStick.maxAttempts);
        drawPng(firstMStick, 2L);

        TwoByTwoMatchStick secondMStick = new TwoByTwoMatchStick(new GaussianNoiseMapper());
        secondMStick.setProperties(40, "SHADE");
        secondMStick.genMorphedBaseMatchStick(firstMStick, 1, secondMStick.maxAttempts, true, true, 0.7, 1 / 3.0);
        drawPng(secondMStick, 3L);

        TwoByTwoMatchStick thirdMStick = new TwoByTwoMatchStick(new GaussianNoiseMapper());
        thirdMStick.setProperties(40, "SHADE");
        thirdMStick.genMorphedDrivingComponentMatchStick(firstMStick, 0.5, 0.5, true, true, firstMStick.maxAttempts);
        drawPng(thirdMStick, 4L);

        TwoByTwoMatchStick fourthMStick = new TwoByTwoMatchStick(new GaussianNoiseMapper());
        fourthMStick.setProperties(40, "SHADE");
        fourthMStick.genSwappedBaseAndDrivingComponentMatchStick(secondMStick, 1, thirdMStick, true, 15);
        drawPng(fourthMStick, 5L);
    }

    @Test
    public void test_partially_inside(){
        EStimShapeTwoByTwoMatchStick firstMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF, null);
        firstMStick.setProperties(5, "SHADE");
        firstMStick.genMatchStickFromComponent(baseMStick, 1, 2, firstMStick.maxAttempts);
        drawPng(firstMStick, 11L);


        EStimShapeTwoByTwoMatchStick secondMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF, null);
        secondMStick.setProperties(5, "SHADE");
        secondMStick.genMorphedBaseMatchStick(firstMStick, 1, secondMStick.maxAttempts, true, true, 0.7, 1 / 3.0);
        drawPng(secondMStick, 12L);

        EStimShapeTwoByTwoMatchStick thirdMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF, null);
        thirdMStick.setProperties(5, "SHADE");
        thirdMStick.genMorphedDrivingComponentMatchStick(firstMStick, 0.5, 0.5, true, true, firstMStick.maxAttempts);
        drawPng(thirdMStick, 13L);

        EStimShapeTwoByTwoMatchStick fourthMStick = new EStimShapeTwoByTwoMatchStick(RFStrategy.PARTIALLY_INSIDE, PARTIAL_RF, null);
        fourthMStick.setProperties(5, "SHADE");
        fourthMStick.genSwappedBaseAndDrivingComponentMatchStick(secondMStick, 1, thirdMStick, true, 15);
        drawPng(fourthMStick, 14L);
    }

    private void drawPng(TwoByTwoMatchStick matchStick, long id) {
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