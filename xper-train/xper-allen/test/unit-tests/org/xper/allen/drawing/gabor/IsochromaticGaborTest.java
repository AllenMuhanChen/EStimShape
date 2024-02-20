package org.xper.allen.drawing.gabor;

import org.junit.Before;
import org.junit.Test;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.drawing.TestDrawingWindow;
import org.xper.rfplot.drawing.GratingSpec;
import org.xper.util.ThreadUtil;

public class IsochromaticGaborTest {

    private TestDrawingWindow window;
    private int height;
    private int width;

    @Before
    public void setUp() throws Exception {

        height = 1000;
        width = 1000;
        window = TestDrawingWindow.createDrawerWindow(width, height);

    }

    @Test
    public void testDraw() {
        GratingSpec spec = new GratingSpec();
        spec.setOrientation(0);
        spec.setPhase(0);
        spec.setFrequency(10);
        spec.setXCenter(0);
        spec.setYCenter(0);
        spec.setSize(5);
        spec.setAnimation(false);


        IsochromaticGabor gabor = new IsochromaticGabor();
        gabor.setSpec(spec);

        window.draw(new Drawable() {
            @Override
            public void draw() {
                IsochromaticGabor.initGL(width, height);
                gabor.draw(null);
            }
        });

        ThreadUtil.sleep(1000);
    }
}