package org.xper.allen.pga;

import org.junit.Before;
import org.junit.Ignore;
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
    private String figPath;

    @Before
    public void setUp() throws Exception {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));


        generator = context.getBean(FromDbGABlockGenerator.class);

        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup(500, 500);

        figPath = "/home/r2_allen/Pictures";
    }

    @Test
    public void test_regime_zero_stim(){
        SeedingStim seedingStim = new SeedingStim(1L,
                generator,
                "SHADE",
                new RGBColor(1.0, 1.0, 1.0)
        );
        seedingStim.setProperties();
        GAMatchStick mStick = seedingStim.createMStick();
        testMatchStickDrawer.drawMStick(mStick);
        testMatchStickDrawer.drawCompMap(mStick);
        ThreadUtil.sleep(10000);

    }

    @Test
    public void test_zooming_stim_from_regime_zero(){
        SeedingStim seedingStim = new SeedingStim(1L,
                generator,
                "SHADE",
                new RGBColor(1.0, 1.0, 1.0)
        );
        seedingStim.setProperties();

        GAMatchStick mStick = seedingStim.createMStick();
        testMatchStickDrawer.drawMStick(mStick);
        testMatchStickDrawer.drawCompMap(mStick);
        testMatchStickDrawer.saveSpec(mStick, generator.getGeneratorSpecPath() + "/" + Long.toString(1L));
        ThreadUtil.sleep(1000);

        ZoomingStim zoomingStim = new ZoomingStim(2L,
                generator,
                1L,
                1,
                "SHADE"
                );
        zoomingStim.setProperties();

        GAMatchStick mStick1 = zoomingStim.createMStick();
        testMatchStickDrawer.clear();
        testMatchStickDrawer.drawMStick(mStick1);
        testMatchStickDrawer.drawCompMap(mStick1);
        ThreadUtil.sleep(1000);

        ZoomingStim zoomingStim2 = new ZoomingStim(3L,
                generator,
                1L,
                2,
                "SHADE");
        zoomingStim2.setProperties();
        GAMatchStick mStick2 = zoomingStim2.createMStick();
        testMatchStickDrawer.drawMStick(mStick2);
        testMatchStickDrawer.drawCompMap(mStick2);
        ThreadUtil.sleep(1000);
    }

    @Ignore
    @Test
    public void fig_examples_of_partial_and_complete_inside_rf(){

        SeedingStim seedingStim = new SeedingStim(1L,
                generator,
                "SHADE",
                new RGBColor(1.0, 1.0, 1.0)
        );

        GAMatchStick mStick = seedingStim.createMStick();
        testMatchStickDrawer.drawMStick(mStick);
        testMatchStickDrawer.drawRF(mStick);
        testMatchStickDrawer.saveSpec(mStick, generator.getGeneratorSpecPath() + "/" + Long.toString(1L));
        testMatchStickDrawer.saveImage(figPath +"/complete_inside_rf.png");
        ThreadUtil.sleep(1000);

        ZoomingStim zoomingStim = new ZoomingStim(2L,
                generator,
                1L,
                1,
                "SHADE"
                );

        GAMatchStick mStick1 = zoomingStim.createMStick();
        testMatchStickDrawer.clear();
        testMatchStickDrawer.drawMStick(mStick1);
        testMatchStickDrawer.drawRF(mStick1);
        testMatchStickDrawer.saveImage(figPath +"/zooming_stim.png");
        ThreadUtil.sleep(1000);
    }

    @Ignore
    @Test
    public void fig_examples_of_seeding_stim(){

        int numStim = 5;
        for (int i = 0; i < numStim; i++){
            SeedingStim seedingStim = new SeedingStim((long)i,
                    generator,
                    "SHADE",
                    new RGBColor(1.0, 1.0, 1.0)
            );

            GAMatchStick mStick = seedingStim.createMStick();
            testMatchStickDrawer.drawMStick(mStick);
            testMatchStickDrawer.drawRF(mStick);
            testMatchStickDrawer.saveSpec(mStick, figPath +"/seeding_stim_" + Integer.toString(i));
            testMatchStickDrawer.saveImage(figPath +"/seeding_stim_" + Integer.toString(i) + ".png");
            ThreadUtil.sleep(100);
            testMatchStickDrawer.clear();
        }
    }



}