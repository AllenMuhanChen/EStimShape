package org.xper.allen.drawing.composition;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.util.CoordinateConverter;
import org.xper.allen.util.CoordinateConverter.SphericalCoordinates;
import org.xper.drawing.TestDrawingWindow;
import org.xper.util.ThreadUtil;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.util.List;

public class AllenMStickDataTest {

    private TestDrawingWindow window;

    @Test
    public void AllenMStickSpecGeneratesData() {
       AllenMatchStick matchStick = new AllenMatchStick();
       matchStick.setProperties(5);
       matchStick.genMatchStickRand();

       AllenMStickData data = matchStick.getMStickData();
       drawMStick(matchStick);
       for (int i=0; i<data.getShaftData().size(); i++) {
           double length = data.getShaftData().get(i).length;
           System.out.println("length: " + length);

           AngularCoordinates angularPosition = data.getShaftData().get(i).angularPosition;
           double radialPosition = data.getShaftData().get(i).radialPosition;

           Point3d massCenter = matchStick.getMassCenter();

           Vector3d shaftAxis = CoordinateConverter.sphericalToVector(new SphericalCoordinates(radialPosition, angularPosition));
           List<Point3d> shaftLine = CoordinateConverter.vectorToLine(shaftAxis, 100, massCenter);

           for(Point3d point:shaftLine){
               //point.set(new Point3d(deg2mm(point.x), deg2mm(point.y), deg2mm(point.z)+50));
               point.set(new Point3d(point.x, point.y, point.z+10));
               System.out.println(point);
           }

           drawLine(shaftLine,(i+1)/2,1,0);
       }



       ThreadUtil.sleep(100000);



    }

    private double deg2mm(double degrees) {
        return window.renderer.deg2mm(degrees);
    }

    private TestDrawingWindow getTestDrawingWindow() {
        window = TestDrawingWindow.createDrawerWindow();
        return window;
    }

    @Before
    public void setUp() throws Exception {
        getTestDrawingWindow();
    }

    @After
    public void tearDown() throws Exception {
        window.close();
    }

    private void drawMStick(AllenMatchStick mStick){
        window.draw(new Drawable() {
            @Override
            public void draw() {mStick.draw();
            }
        });
    }


    private void drawLine(List<Point3d> line, float red, float green, float blue){

        window.draw(new Drawable() {
            @Override
            public void draw() {
                int i;
                GL11.glColor3f(red, green, blue);
                GL11.glBegin(GL11.GL_LINE_STRIP);
                GL11.glLineWidth(1000);
                for (i=0; i<line.size(); i++)
                {
                    //GL11.glVertex3d(mPts[i].getX(), mPts[i].getY(), mPts[i].getZ());
                    GL11.glVertex3d( line.get(i).x, line.get(i).y, line.get(i).z);
                }

                GL11.glEnd();
            }
        });

    }

}