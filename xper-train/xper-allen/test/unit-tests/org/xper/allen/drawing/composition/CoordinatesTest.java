package org.xper.allen.drawing.composition;

import org.junit.Before;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.experiment.EStimShapeProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.util.ThreadUtil;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.awt.*;

public class CoordinatesTest {
    private final GaussianNoiseMapper noiseMapper = new GaussianNoiseMapper();
    private TestMatchStickDrawer testMatchStickDrawer;
    private EStimShapeProceduralMatchStick mStick;
    private ProceduralMatchStick baseMStick;

    @Before
    public void setUp() throws Exception {
        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup(500, 500);

        baseMStick = genBaseMStick();


    }

    private void genTotallyInsideRFMStick() {
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
        mStick = new EStimShapeProceduralMatchStick(RFStrategy.COMPLETELY_INSIDE, receptiveField, noiseMapper);
        mStick.setProperties(2, "SHADE", 1.0);

        mStick.genMatchStickFromComponentInNoise(baseMStick, 1, 3, true, mStick.maxAttempts, noiseMapper);
    }

    private static ProceduralMatchStick genBaseMStick() {
        ProceduralMatchStick baseMStick = new ProceduralMatchStick(new GaussianNoiseMapper());
        baseMStick.setProperties(4, "SHADE", 1.0);
        baseMStick.setStimColor(new Color(255,255,255));
        baseMStick.genMatchStickRand();
        baseMStick.setMaxAttempts(-1);
        return baseMStick;
    }

    private void genPartiallyInsideRFStick(){
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
        mStick = new EStimShapeProceduralMatchStick(RFStrategy.PARTIALLY_INSIDE, receptiveField, noiseMapper);
        mStick.setProperties(2, "SHADE", 1.0);

        mStick.genMatchStickFromComponentInNoise(baseMStick, 1, 3, true, mStick.maxAttempts, noiseMapper);
    }

    @Test
    public void compare_coordinates(){
//        genTotallyInsideRFMStick();
        genPartiallyInsideRFStick();
        drawRF();
        drawCompVects();
        ThreadUtil.sleep(1000);
        testMatchStickDrawer.drawMStick(mStick);

        ThreadUtil.sleep(10000);

    }

    private void drawCompVects() {
        testMatchStickDrawer.draw(new Drawable() {
            @Override
            public void draw() {
                for (int compId = 1; compId <= mStick.getnComponent(); compId++) {

                    Point3d[] vectInfo = mStick.getComp()[compId].getVect_info();

                    int[][] facInfo = mStick.getComp()[compId].getFacInfo();
                    Vector3d[] normMatInfo = mStick.getComp()[compId].getNormMat_info();
                    int nFac = mStick.getComp()[compId].getnFac();
                    drawVect(vectInfo, facInfo, normMatInfo, nFac);
                }
            }
        });
    }

    public void drawVect(Point3d[] vect_info, int[][] facInfo, Vector3d[] normMat_info, int nFac) {
        GL11.glColor3f(0, 1, 0);

        for (int i = 0; i< nFac; i++) {
            GL11.glBegin(GL11.GL_TRIANGLES);


            Point3d p1 = vect_info[ facInfo[i][0]];
            Point3d p2 = vect_info[ facInfo[i][1]];
            Point3d p3 = vect_info[ facInfo[i][2]];
            Vector3d v1 = normMat_info[ facInfo[i][0]];
            Vector3d v2 = normMat_info[ facInfo[i][1]];
            Vector3d v3 = normMat_info[ facInfo[i][2]];

            GL11.glNormal3d( v1.x, v1.y, v1.z);
            GL11.glVertex3d( p1.x, p1.y, p1.z);
            GL11.glNormal3d( v2.x, v2.y, v2.z);
            GL11.glVertex3d( p2.x, p2.y, p2.z);
            GL11.glNormal3d( v3.x, v3.y, v3.z);
            GL11.glVertex3d( p3.x, p3.y, p3.z);

            GL11.glEnd();
        }
        GL11.glDisable(GL11.GL_LIGHTING);
    }


    private void drawRF() {
        //draw rf
        GL11.glColor3f(1, 0, 0);
        GL11.glBegin(GL11.GL_LINE_LOOP);
        for (Coordinates2D point : mStick.rf.getOutline()) {
            GL11.glVertex2d(point.getX(), point.getY());
        }
        GL11.glEnd();
    }
}