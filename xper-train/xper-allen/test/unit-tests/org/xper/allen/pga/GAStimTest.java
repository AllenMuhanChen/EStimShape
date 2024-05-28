package org.xper.allen.pga;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

public class GAStimTest {

    private FromDbGABlockGenerator generator;
    private TestMatchStickDrawer testMatchStickDrawer;

    @Before
    public void setUp() throws Exception {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));


        generator = context.getBean(FromDbGABlockGenerator.class);

        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup(500, 500);
    }

    @Test
    public void test_regime_zero_stim(){
        SeedingStim seedingStim = new SeedingStim(1L,
                generator,
                new Coordinates2D(0,0),
                "SHADE",
                new RGBColor(1.0, 1.0, 1.0),
                RFStrategy.COMPLETELY_INSIDE);

        GAMatchStick mStick = seedingStim.createMStick();
        testMatchStickDrawer.drawMStick(mStick);
        testMatchStickDrawer.drawCompMap(mStick);
        ThreadUtil.sleep(10000);

    }

    @Test
    public void test_zooming_stim_from_regime_zero(){
        SeedingStim seedingStim = new SeedingStim(1L,
                generator,
                new Coordinates2D(0,0),
                "SHADE",
                new RGBColor(1.0, 1.0, 1.0),
                RFStrategy.COMPLETELY_INSIDE);

        GAMatchStick mStick = seedingStim.createMStick();
        testMatchStickDrawer.drawMStick(mStick);
        testMatchStickDrawer.drawCompMap(mStick);
        testMatchStickDrawer.saveSpec(mStick, generator.getGeneratorSpecPath() + "/" + Long.toString(1L));
        ThreadUtil.sleep(1000);

        ZoomingStim zoomingStim = new ZoomingStim(2L,
                generator,
                1L,
                1,
                new Coordinates2D(0,0),
                0.5,
                "SHADE",
                new RGBColor(1.0, 1.0, 1.0));

        GAMatchStick mStick1 = zoomingStim.createMStick();
        testMatchStickDrawer.clear();
        testMatchStickDrawer.drawMStick(mStick1);
        testMatchStickDrawer.drawCompMap(mStick1);
        ThreadUtil.sleep(1000);

        ZoomingStim zoomingStim2 = new ZoomingStim(3L,
                generator,
                1L,
                2,
                new Coordinates2D(0,0),
                0.5,
                "SHADE",
                new RGBColor(1.0, 1.0, 1.0));

        GAMatchStick mStick2 = zoomingStim2.createMStick();
        testMatchStickDrawer.drawMStick(mStick2);
        testMatchStickDrawer.drawCompMap(mStick2);
        ThreadUtil.sleep(1000);
    }
}