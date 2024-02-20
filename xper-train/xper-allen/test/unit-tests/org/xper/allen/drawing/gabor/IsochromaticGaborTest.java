package org.xper.allen.drawing.gabor;

import org.junit.Before;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.drawing.RGBColor;
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
    public void testIsochromatic() {
        GratingSpec spec = new GratingSpec();
        spec.setOrientation(0);
        spec.setPhase(0);
        spec.setFrequency(10);
        spec.setXCenter(0);
        spec.setYCenter(0);
        spec.setSize(50);
        spec.setAnimation(false);


        IsochromaticGabor gabor = new IsochromaticGabor(new RGBColor(1,0,0));
        gabor.setSpec(spec);

        window.draw(new Drawable() {
            @Override
            public void draw() {
                GL11.glClearColor(0.5f, 0.5f, 0.5f, 1.0f);
                GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
                IsochromaticGabor.initGL(width, height);
                gabor.draw(null);
            }
        });

        ThreadUtil.sleep(10000);
    }

    @Test
    public void testIsoluminant() {
        GratingSpec spec = new GratingSpec();
        spec.setOrientation(0);
        spec.setPhase(0);
        spec.setFrequency(10);
        spec.setXCenter(0);
        spec.setYCenter(0);
        spec.setSize(50);
        spec.setAnimation(false);

        IsoluminantGabor gabor = new IsoluminantGabor(new RGBColor(0, 0.5f, 0.5f), new RGBColor(0.5f, 0.5f, 0),
                true, true);
        gabor.setSpec(spec);

        window.draw(new Drawable() {
            @Override
            public void draw() {
                GL11.glClearColor(0.5f, 0.5f, 0.5f, 1.0f);
                GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
                IsoluminantGabor.initGL(width, height);
                gabor.draw(null);
            }
        });

        ThreadUtil.sleep(100000);

    }
}