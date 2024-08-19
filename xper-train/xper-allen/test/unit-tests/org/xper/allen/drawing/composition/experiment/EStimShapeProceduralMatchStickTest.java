package org.xper.allen.drawing.composition.experiment;

import org.junit.Before;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.AllenDrawingManager;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.composition.noisy.NoiseMapper;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.TestDrawingWindow;
import org.xper.util.FileUtil;
import org.xper.util.ResourceUtil;
import org.xper.util.ThreadUtil;

import javax.vecmath.Point3d;
import java.awt.*;
import java.util.Collections;

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
    private JavaConfigApplicationContext context;
    private NoiseMapper noiseMapper = new GaussianNoiseMapper();

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup(500, 500);

        baseMStick = new ProceduralMatchStick(new GaussianNoiseMapper());
        baseMStick.setProperties(4, "SHADE");
        baseMStick.setStimColor(new Color(255,255,255));
        baseMStick.genMatchStickRand();
        baseMStick.setMaxAttempts(-1);


    }

    @Test
    public void test_completely_in_RF(){
//        pngMaker.createDrawerWindow();

        ReceptiveField receptiveField = new ReceptiveField() {
            final double h = 30;
            final double k = 30;
            final double r = 10;

            {
                center = new Coordinates2D(h, k);
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
        EStimShapeProceduralMatchStick mStick = new EStimShapeProceduralMatchStick(RFStrategy.COMPLETELY_INSIDE, receptiveField, noiseMapper);

        mStick.setProperties(2.5, "SHADE");

        mStick.genMatchStickFromComponentInNoise(baseMStick, 1, 3, true, mStick.maxAttempts, noiseMapper);
        testMatchStickDrawer.draw(new Drawable() {
            @Override
            public void draw() {
                mStick.draw();

                // Now, draw the circle
                GL11.glColor3f(1.0f, 0.0f, 0.0f);
                System.out.println(mStick.getSpecialEndComp().get(0));
                Point3d circle = mStick.calculateGaussNoiseOrigin(mStick.getSpecialEndComp().get(0)); // Replace with the circle's center X-coordinate

                System.out.println(circle.getX() + " " + circle.getY());

                double radius = mStick.noiseRadiusMm;
                int numSegments = 100; // Increase for a smoother circle

                GL11.glBegin(GL11.GL_LINE_LOOP);
                for (int i = 0; i < numSegments; i++) {
                    double theta = 2.0 * Math.PI * i / numSegments; // Current angle
                    double x = radius * Math.cos(theta); // Calculate the x component
                    double y = radius * Math.sin(theta); // Calculate the y component
                    GL11.glVertex2d(x + circle.getX(), y + circle.getY()); // Output vertex
                }
                GL11.glEnd();
            }






        });

        ThreadUtil.sleep(1000);
        testMatchStickDrawer.clear();
        testMatchStickDrawer.draw(new Drawable() {
            @Override
            public void draw() {
                // Now, draw the circle
                GL11.glColor3f(1.0f, 0.0f, 0.0f);
                System.out.println(mStick.getSpecialEndComp().get(0));
                Point3d circle = mStick.calculateGaussNoiseOrigin(mStick.getSpecialEndComp().get(0)); // Replace with the circle's center X-coordinate
                System.out.println(circle.getX() + " " + circle.getY());

                double radius = 10;
                int numSegments = 100; // Increase for a smoother circle

                GL11.glBegin(GL11.GL_LINE_LOOP);
                for (int i = 0; i < numSegments; i++) {
                    double theta = 2.0 * Math.PI * i / numSegments; // Current angle
                    double x = radius * Math.cos(theta); // Calculate the x component
                    double y = radius * Math.sin(theta); // Calculate the y component
                    GL11.glVertex2d(x + circle.getX(), y + circle.getY()); // Output vertex
                }
                GL11.glEnd();
                mStick.drawCompMap();
            }
        });

        ThreadUtil.sleep(10000);

    }

    @Test
    public void test_partially_in_RF(){
//        pngMaker.createDrawerWindow();

        ReceptiveField receptiveField = new ReceptiveField() {
            final double h = 30;
            final double k = 30;
            final double r = 10;

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
                return (x- h)*(x- h) + (y- k)*(y- k) < r * r;
            }
        };
        EStimShapeProceduralMatchStick mStick = new EStimShapeProceduralMatchStick(
                RFStrategy.PARTIALLY_INSIDE, receptiveField, noiseMapper);

        mStick.setProperties(4.5, "SHADE");

        mStick.genMatchStickFromComponentInNoise(baseMStick, 1, 3, true, mStick.maxAttempts, noiseMapper);
        testMatchStickDrawer.draw(new Drawable() {
            @Override
            public void draw() {
                mStick.drawCompMap();


                // Now, draw the circle
                GL11.glColor3f(1.0f, 0.0f, 0.0f);
                Point3d circle = mStick.calculateGaussNoiseOrigin(mStick.getSpecialEndComp().get(0)); // Replace with the circle's center X-coordinate


                double radius = mStick.noiseRadiusMm;
                int numSegments = 100; // Increase for a smoother circle

                GL11.glBegin(GL11.GL_LINE_LOOP);
                for (int i = 0; i < numSegments; i++) {
                    double theta = 2.0 * Math.PI * i / numSegments; // Current angle
                    double x = radius * Math.cos(theta); // Calculate the x component
                    double y = radius * Math.sin(theta); // Calculate the y component
                    GL11.glVertex2d(x + circle.getX(), y + circle.getY()); // Output vertex
                }
                GL11.glEnd();

                mStick.draw();
            }


        });

        ThreadUtil.sleep(10000);


    }

    @Test
    public void draw_noisemap_partially_in_rf(){
        ReceptiveField receptiveField = new ReceptiveField() {
            final double h = 5;
            final double k = 5;
            final double r = 10;

            {
                center = new Coordinates2D(h, k);
                radius=r;
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
        EStimShapeProceduralMatchStick mStick = new EStimShapeProceduralMatchStick(
                RFStrategy.PARTIALLY_INSIDE, receptiveField, noiseMapper);

        mStick.setProperties(5, "SHADE");

        mStick.genMatchStickFromComponentInNoise(baseMStick, 1, 3, true, mStick.maxAttempts, noiseMapper);

        drawPng(mStick, "partially_in_rf");
    }

    public void drawPng(ProceduralMatchStick matchStick, String label) {
        testMatchStickDrawer.stop();
        pngMaker = context.getBean(AllenPNGMaker.class);
        pngMaker.createDrawerWindow();
        drawingManager = pngMaker.window;
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(matchStick, true);
        spec.writeInfo2File(testBin + "/" + label, true);
        pngMaker.createAndSavePNG(matchStick, 1L, Collections.singletonList(Long.toString(1)), testBin);
        pngMaker.createAndSaveGaussNoiseMap(matchStick, 1L, Collections.singletonList(Long.toString(1)), testBin, 0.5, 1);
    }


}