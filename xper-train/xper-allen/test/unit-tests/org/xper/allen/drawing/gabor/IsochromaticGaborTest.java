package org.xper.allen.drawing.gabor;

import org.junit.Before;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.alden.drawing.renderer.PerspectiveRenderer;
import org.xper.drawing.Context;
import org.xper.drawing.RGBColor;
import org.xper.drawing.TestDrawingWindow;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.IsochromaticGaborSpec;
import org.xper.util.ThreadUtil;

public class IsochromaticGaborTest {

    private TestDrawingWindow window;
    private int height;
    private int width;
    private org.xper.drawing.renderer.PerspectiveRenderer perspectiveRenderer;
    private Context context;

    @Before
    public void setUp() throws Exception {

        height = 1000;
        width = 1000;
        window = TestDrawingWindow.createDrawerWindow(height, width);
        PerspectiveRenderer renderer = window.renderer;
        perspectiveRenderer = new org.xper.drawing.renderer.PerspectiveRenderer();
        perspectiveRenderer.setDepth(renderer.getDepth());
        perspectiveRenderer.setHeight(renderer.getHeight());
        perspectiveRenderer.setWidth(renderer.getWidth());
        perspectiveRenderer.setPupilDistance(renderer.getPupilDistance());
        perspectiveRenderer.setDistance(renderer.getDistance());
        perspectiveRenderer.init(width, height);
        perspectiveRenderer.setup();
        perspectiveRenderer.init();

        context = new Context();
        System.out.println(perspectiveRenderer.mm2deg(perspectiveRenderer.getVpWidthmm()));
        context.setRenderer(perspectiveRenderer);
    }

    @Test
    public void testIsochromatic() {
        IsochromaticGaborSpec spec = new IsochromaticGaborSpec();
        spec.setOrientation(0);
        spec.setPhase(0);
        spec.setFrequency(10);
        spec.setXCenter(0);
        spec.setYCenter(0);
        spec.setSize(6);
        spec.setAnimation(false);
        spec.setColor(new RGBColor(1f, 0f, 0f));


        IsochromaticGabor gabor = new IsochromaticGabor();
        gabor.setSpec(spec.toXml());

        window.draw(new Drawable() {
            @Override
            public void draw() {
                GL11.glClearColor(0.5f, 0.5f, 0.5f, 1.0f);
                GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
                IsochromaticGabor.initGL(width, height);
                gabor.draw(context);
            }
        });

        ThreadUtil.sleep(10000);
    }

    @Test
    public void testIsoluminant() {
        int size = 6;
        GaborSpec spec = new GaborSpec();
        spec.setOrientation(125);
        spec.setPhase(0);
        spec.setFrequency(2);
        spec.setXCenter(3);
        spec.setYCenter(3);
        spec.setSize(size);
        spec.setAnimation(false);

        IsoluminantGabor gabor = new IsoluminantGabor(new RGBColor(0, 0.5f, 0.5f), new RGBColor(0.5f, 0.5f, 0),
                true, true);
        gabor.setSpec(spec.toXml());

        window.draw(new Drawable() {
            @Override
            public void draw() {
                GL11.glClearColor(0.5f, 0.5f, 0.5f, 1.0f);
                GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
                IsoluminantGabor.initGL(width, height);
                gabor.draw(context);
            }
        });

        double ratio = perspectiveRenderer.deg2mm(size) / perspectiveRenderer.getVpWidthmm();
        System.out.println("The Gabor should span approx: " + ratio + " of the screen width.");

        ThreadUtil.sleep(100000);

    }
}