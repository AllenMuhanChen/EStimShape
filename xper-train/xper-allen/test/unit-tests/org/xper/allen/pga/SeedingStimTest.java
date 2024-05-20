package org.xper.allen.pga;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

public class SeedingStimTest {

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
        testMatchStickDrawer.draw(new Drawable() {
            @Override
            public void draw() {
                mStick.drawCompMap();
            }
        });
        ThreadUtil.sleep(10000);

    }
}