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
import org.xper.rfplot.drawing.gabor.ColourConverter;
import org.xper.rfplot.drawing.gabor.IsochromaticGabor;
import org.xper.rfplot.drawing.gabor.IsoluminantGabor;
import org.xper.rfplot.drawing.gabor.IsoluminantGaborSpec;
import org.xper.util.ThreadUtil;

import java.awt.*;

public class IsochromaticGaborTest {

    private TestDrawingWindow window;
    private int height;
    private int width;
    private org.xper.drawing.renderer.PerspectiveRenderer perspectiveRenderer;
    private Context context;

    @Before
    public void setUp() throws Exception {

        height = 1000;
        width = 1500;
        window = TestDrawingWindow.createDrawerWindow(height, width);
        PerspectiveRenderer renderer = window.renderer;
        perspectiveRenderer = new org.xper.drawing.renderer.PerspectiveRenderer();
        perspectiveRenderer.setDepth(renderer.getDepth());
        perspectiveRenderer.setHeight(renderer.getHeight());
        perspectiveRenderer.setWidth(renderer.getWidth());
        perspectiveRenderer.setPupilDistance(renderer.getPupilDistance());
        perspectiveRenderer.setDistance(renderer.getDistance());
        perspectiveRenderer.init(width, height);


        context = new Context();
        System.out.println(perspectiveRenderer.mm2deg(perspectiveRenderer.getVpWidthmm()));
        context.setRenderer(perspectiveRenderer);
    }

    @Test
    public void testIsochromatic() {
        IsochromaticGaborSpec spec = new IsochromaticGaborSpec();
        spec.setOrientation(45);
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
        int size = 20;
        GaborSpec spec = new GaborSpec();
        spec.setOrientation(45);
        spec.setPhase(0);
        spec.setFrequency(2);
        spec.setXCenter(0);
        spec.setYCenter(0);
        spec.setSize(size);
        spec.setAnimation(false);

//        IsoluminantGaborSpec isoluminantGaborSpec = new IsoluminantGaborSpec(new RGBColor(0.5f, 0.5f, 0),
//                new RGBColor(0, 0.5f, 0.5f), false, true, spec);
        IsoluminantGaborSpec isoluminantGaborSpec = new IsoluminantGaborSpec(
                new RGBColor(1f, 0f, 0f),
                new RGBColor(0f, 1f, 0f), true, true, spec);
        IsoluminantGabor gabor = new IsoluminantGabor();
        gabor.setGaborSpec(isoluminantGaborSpec);
        gabor.setSpec(isoluminantGaborSpec.toXml());

        window.draw(new Drawable() {
            @Override
            public void draw() {
                GL11.glClearColor(0.5f, 0.5f, 0.5f, 1.0f);
                GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
                gabor.draw(context);
            }
        });

        double ratio = perspectiveRenderer.deg2mm(size) / perspectiveRenderer.getVpWidthmm();
        System.out.println("The Gabor should span approx: " + ratio + " of the screen width.");

        ThreadUtil.sleep(100000);

    }

    @Test
    public void testIsoluminantColors(){
        Color gray = new Color(0.5f, 0.5f, 0.5f);
        double gray_lab[] = ColourConverter.getLab(gray, ColourConverter.WhitePoint.D65);
        System.out.println("Gray: " + gray_lab[0] + " " + gray_lab[1] + " " + gray_lab[2]);

        Color red = new Color(1f, 0f, 0f);
        double red_lab[] = ColourConverter.getLab(red, ColourConverter.WhitePoint.D65);
        System.out.println("Red Lab: " + red_lab[0] + " " + red_lab[1] + " " + red_lab[2]);

        Color green = new Color(0f, 1f, 0f);
        double green_lab[] = ColourConverter.getLab(green, ColourConverter.WhitePoint.D65);
        System.out.println("Green Lab: " + green_lab[0] + " " + green_lab[1] + " " + green_lab[2]);

        // Match the green to the gray
        double l = gray_lab[0];
        double a = green_lab[1];
        double b = green_lab[2];

        double[] modulatedRGB = ColourConverter.labToRGB(l, a, b, ColourConverter.WhitePoint.D65);
        System.out.println("New Green RGB: " + modulatedRGB[0] + " " + modulatedRGB[1] + " " + modulatedRGB[2]);

        //Match the red to the gray
        a = red_lab[1];
        b = red_lab[2];
        modulatedRGB = ColourConverter.labToRGB(l, a, b, ColourConverter.WhitePoint.D65);
        System.out.println("New Red RGB: " + modulatedRGB[0] + " " + modulatedRGB[1] + " " + modulatedRGB[2]);


    }

    @Test
    public void testIsoluminantRGBS(){
        Color gray = new Color(0.5f, 0.5f, 0.5f);
        double gray_lab[] = ColourConverter.getLab(gray, ColourConverter.WhitePoint.D65);
        double target_L = gray_lab[0];

        Color red = new Color(1f, 0f, 0f);
        double red_lab[] = ColourConverter.getLab(red, ColourConverter.WhitePoint.D65);
        double red_target_b = red_lab[2];


        Color green = new Color(0f, 1f, 0f);
        double green_lab[] = ColourConverter.getLab(green, ColourConverter.WhitePoint.D65);
        double green_target_b = green_lab[2];

        //RED
        double a = 100;
        double[] rgb;
        while(true){
            rgb = ColourConverter.labToRGB(target_L, a, red_target_b, ColourConverter.WhitePoint.D65);
            //if all values are between 0 and 1, break
            if(rgb[0] >= 0 && rgb[0] <= 1 && rgb[1] >= 0 && rgb[1] <= 1 && rgb[2] >= 0 && rgb[2] <= 1){
                break;
            }
            a = a - 0.1;
        }
        System.out.println("Red RGB: " + rgb[0] + " " + rgb[1] + " " + rgb[2]);

        //GREEN
        a = -100;
        while(true){
            rgb = ColourConverter.labToRGB(target_L, a, 60, ColourConverter.WhitePoint.D65);
            //if all values are between 0 and 1, break
            if(rgb[0] >= 0 && rgb[0] <= 1 && rgb[1] >= 0 && rgb[1] <= 1 && rgb[2] >= 0 && rgb[2] <= 1){
                break;
            }
            a = a + 0.1;
//            System.out.println(a);
        }
        System.out.println("Green RGB: " + rgb[0] + " " + rgb[1] + " " + rgb[2]);
    }
}