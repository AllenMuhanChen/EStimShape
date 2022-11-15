package org.xper.allen.drawing.composition;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.xper.XperConfig;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.drawing.TestDrawingWindow;
import org.xper.drawing.stick.MAxisArc;
import org.xper.util.ThreadUtil;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import java.util.ArrayList;
import java.util.List;

public class AllenMAxisArcTest {

    public static final Vector3d VIEW_SIDE = new Vector3d(1, 0, 0);
    public static final Vector3d VIEW_ABOVE = new Vector3d(0, 1, 0);
    private final Vector3d VIEW_TANGENT = new Vector3d(0, 0, 1);

    @Before
    public void setUp(){
        List<String> libs = new ArrayList<String>();
        libs.add("xper");
        new XperConfig("", libs);
    }

    @After
    public void tearDown(){
//        TestDrawingWindow.close();
    }

    @Test
    public void AllenMAXisArcGenSimilarArcGeneratesSimilarArcs(){
        Vector3d view = VIEW_ABOVE;


        TestDrawingWindow window = TestDrawingWindow.createDrawerWindow();
        AllenMAxisArc allenMAxisArc = new AllenMAxisArc();
        allenMAxisArc.genArc(5,5);
        allenMAxisArc.transRotMAxis(1, new Point3d(0,0,0), 1, view, 0);



        for (int i=0; i<50; i++){
            showNewSimilarArc(window, allenMAxisArc);
        }

        window.draw(new Drawable() {
            @Override
            public void draw() {
                allenMAxisArc.drawArc(1.0f, 0.0f, 0.0f);
            }
        });

        ThreadUtil.sleep(10000);


    }

    private void showNewSimilarArc(TestDrawingWindow window, AllenMAxisArc allenMAxisArc) {
        AllenMAxisArc allenMAxisArc1 = new AllenMAxisArc();
        allenMAxisArc1.genSimilarArc(allenMAxisArc, 1, 0.7);


        window.draw(new Drawable() {
            @Override
            public void draw() {
                allenMAxisArc1.drawArc(1.0f, 1.0f, 0.0f);
            }
        });
    }

    @Test
    public void MAXisArcGenSimilarArcGenerateSimilarArcs(){
        Vector3d view = VIEW_ABOVE;

        TestDrawingWindow window = TestDrawingWindow.createDrawerWindow();
        MAxisArc mAxisArc = new MAxisArc();
        mAxisArc.genArc(5,5);
        mAxisArc.transRotMAxis(1, new Point3d(0,0,0), 1, view, 0);



        for (int i=0; i<50; i++){
            showNewSimilarArc(window, mAxisArc);
        }

        window.draw(new Drawable() {
            @Override
            public void draw() {
                mAxisArc.drawArc(1.0f, 0.0f, 0.0f);
            }
        });

        ThreadUtil.sleep(10000);


    }

    private void showNewSimilarArc(TestDrawingWindow window, MAxisArc mAxisArc) {
        MAxisArc mAxisArc1 = new MAxisArc();
        mAxisArc1.genSimilarArc(mAxisArc, 1, 0.7);


        window.draw(new Drawable() {
            @Override
            public void draw() {
                mAxisArc1.drawArc(1.0f, 1.0f, 0.0f);
            }
        });
    }

    @Test
    /**
     * Have to verify this test by eye, as it's verified by looking at the lines that are drawn. It should draw a fan
     * of lines, each with uniform spacing. Because we are incrementing the devAngle, if the absolute
     * dev angle is drawn, then the position should be incrementing.
     */
    public void AllenMAxisHasAbsoluteDevAngles(){
        TestDrawingWindow window = TestDrawingWindow.createDrawerWindow();
        //AllenMAxis devAngle=0
        AllenMAxisArc allenMAxisArc = new AllenMAxisArc();
        allenMAxisArc.genArc(5,5);
        allenMAxisArc.transRotMAxis(1, new Point3d(0,0,0), 1, VIEW_TANGENT, 0);
        ThreadUtil.sleep(1000);
        window.draw(new Drawable() {
            @Override
            public void draw() {
                allenMAxisArc.drawArc(1.0f, 0.0f, 0.0f);
            }
        });



        //draw
        ThreadUtil.sleep(1000);


        //AllenMAxis devAngle=pi
        AllenMAxisArc allenMAxisArc1 = new AllenMAxisArc();
        allenMAxisArc1.copyFrom(allenMAxisArc);
        allenMAxisArc1.transRotMAxis(1, new Point3d(0,0,0), 1, VIEW_TANGENT, Math.PI/2);
        double deviateAngle = 0;
        for (int i=0; i<100; i++){
            drawArcAtAngle(window, allenMAxisArc1, deviateAngle, 1.0f, 1.0f, 0.0f);
            deviateAngle+=2*Math.PI/100;
            ThreadUtil.sleep(100);
        }

    }

    @Test
    /**
     * In this test, we can see that MAXis's devAngle property is how much to rotate limb from its current position. Since we are
     * continuously incrementing devAngle, the devAngle change each iteration increases.
     */
    public void MAxisHasRelativeDevAngles(){
        TestDrawingWindow window = TestDrawingWindow.createDrawerWindow();
        //MAxisArc devAngle=0
        MAxisArc mAxisArc = new MAxisArc();
        mAxisArc.genArc(5,5);
        mAxisArc.transRotMAxis(1, new Point3d(0,0,0), 1, VIEW_TANGENT, 0);
        ThreadUtil.sleep(1000);
        window.draw(new Drawable() {
            @Override
            public void draw() {
                mAxisArc.drawArc(1.0f, 0.0f, 0.0f);
            }
        });

        //draw
        ThreadUtil.sleep(1000);


        //AllenMAxis devAngle=pi
        MAxisArc mAxisArc1 = new MAxisArc();
        mAxisArc1.copyFrom(mAxisArc);
        double deviateAngle = 0;
        for (int i=0; i<100; i++){
            drawArcAtAngle(window, mAxisArc1, deviateAngle, 1.0f, 1.0f, 0.0f);
            deviateAngle+=2.0*Math.PI/100.0;
            ThreadUtil.sleep(100);
        }
    }

    @Test
    /**
     * In this test, we can see that MAXis changes devAngle by incrementing how much its devAngle moves. Since we are
     * are not incrementing devAngle ourselves, the MAxis steadily rotates itselfs by the devAngle.
     */
    public void MAxisHasContinuousDevAngleChangeWithNoIncrement(){
        TestDrawingWindow window = TestDrawingWindow.createDrawerWindow();
        //MAxisArc devAngle=0
        MAxisArc mAxisArc = new MAxisArc();
        mAxisArc.genArc(5,5);
        mAxisArc.transRotMAxis(1, new Point3d(0,0,0), 1, VIEW_TANGENT, 0);
        ThreadUtil.sleep(1000);
        window.draw(new Drawable() {
            @Override
            public void draw() {
                mAxisArc.drawArc(1.0f, 0.0f, 0.0f);
            }
        });

        //draw
        ThreadUtil.sleep(1000);


        //AllenMAxis devAngle=pi
        MAxisArc mAxisArc1 = new MAxisArc();
        mAxisArc1.copyFrom(mAxisArc);
        double deviateAngle = 2*Math.PI/100;
        for (int i=0; i<100; i++){
            drawArcAtAngle(window, mAxisArc1, deviateAngle, 1.0f, 1.0f, 0.0f);
            deviateAngle+=0;
            ThreadUtil.sleep(100);
        }
    }

    private void drawArcAtAngle(TestDrawingWindow window, MAxisArc mAxisArc1, double deviateAngle, final float red, final float green, final float blue) {
        mAxisArc1.transRotMAxis(1, new Point3d(0,0,0), 1, VIEW_TANGENT, deviateAngle);
        window.draw(new Drawable() {
            @Override
            public void draw() {
                mAxisArc1.drawArc(red, green, blue);
            }
        });
    }

    private void drawArcAtAngle(TestDrawingWindow window, AllenMAxisArc allenMAxisArc1, double deviateAngle, float red, float green, float blue) {
        allenMAxisArc1.transRotMAxis(1, new Point3d(0,0,0), 1, VIEW_TANGENT, deviateAngle);
        window.draw(new Drawable() {
            @Override
            public void draw() {
                allenMAxisArc1.drawArc(red, green, blue);
            }
        });
    }



}