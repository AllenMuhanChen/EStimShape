package org.xper.allen.drawing.ga;

import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.*;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.util.CoordinateConverter;
import org.xper.drawing.RGBColor;
import org.xper.drawing.TestDrawingWindow;
import org.xper.drawing.stick.MatchStick;
import org.xper.drawing.stick.stickMath_lib;

import javax.imageio.ImageIO;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;

import static org.junit.Assert.assertTrue;
import static org.xper.allen.drawing.composition.AllenPNGMaker.screenShotBinary;

public class TestMatchStickDrawer {
    public TestDrawingWindow window;
    private int height;
    private int width;

    private static final LinkedHashMap<Integer, RGBColor> COMP_COLORS = new LinkedHashMap<>();
    static {
        COMP_COLORS.put(0, new RGBColor(1,1,1));
        COMP_COLORS.put(1, new RGBColor(1,0,0));
        COMP_COLORS.put(2, new RGBColor(0,1,0));
        COMP_COLORS.put(3, new RGBColor(0,0,1));
    }

    private static final LinkedHashMap<Integer, RGBColor> JUNC_COLORS = new LinkedHashMap<>();
    static {
        JUNC_COLORS.put(0, new RGBColor(1,1,0));
        JUNC_COLORS.put(1, new RGBColor(1,0,1));
        JUNC_COLORS.put(2, new RGBColor(0,1,1));
    }

    public void setup(int height, int width){
        this.height = height;
        this.width = width;
        window = TestDrawingWindow.createDrawerWindow(height, width);
    }

    public void drawMStick(MatchStick mStick){
        window.draw(new Drawable() {
            @Override
            public void draw() {mStick.draw();
            }
        });
    }


    public void drawGhost(AllenMatchStick mStick){
        window.draw(new Drawable() {
            @Override
            public void draw() {mStick.drawGhost();
            }
        });
    }

    public void stop(){
        window.close();
    }


    public void draw(Drawable drawable){
        window.draw(drawable);
    }

    public void clear(){
        GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT);
    }

    public String saveImage(String filepath){
        byte[] data = screenShotBinary(width,height);

        String path = filepath;
        path=path+".png";

        try {
            FileOutputStream fos = new FileOutputStream(path);
            fos.write(data);
            fos.close();
            return path;
        }

        catch (IOException e) {
            e.printStackTrace();
            return "Error: No Path";
        }
    }

    public String saveNoiseMap(String filepath, ProceduralMatchStick obj, double amplitude, int specialCompIndx) {
        GaussianNoiseMapper noiseMapper = new GaussianNoiseMapper();
        noiseMapper.setDoEnforceHiddenJunction(false);
        BufferedImage img = noiseMapper.generateGaussianNoiseMapFor(obj,
                width, height,
                amplitude,  0, window.renderer, specialCompIndx);

        filepath=filepath+".png";
        File ouptutFile = new File(filepath);
        try {
            ImageIO.write(img, "png", ouptutFile);
        } catch (IOException e) {
            e.printStackTrace();
        }
        return ouptutFile.getAbsolutePath();
    }

    public AllenMStickSpec saveSpec(AllenMatchStick mStick, String filepath) {
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(mStick, true);
        spec.writeInfo2File(filepath, true);
        return spec;
    }

    public void drawCompMap(AllenMatchStick mStick) {
        window.draw(new Drawable() {
            @Override
            public void draw() {
                mStick.drawCompMap();
            }
        });
    }

    public void drawRF(GAMatchStick mStick) {
        window.draw(new Drawable() {
            @Override
            public void draw() {
                mStick.drawRF();
            }
        });
    }

    public void drawMStickData(AllenMatchStick mStick, AllenMStickData data){
        int numShafts = data.getShaftData().size();
        List<Point3d> shaftPositions = getShaftPositions(data);
        drawShaftPositions(numShafts, shaftPositions);

        List<Point3d> jucPositions = getJuncPositions(data);
        drawJuncPositions(jucPositions);

        List<Point3d> endPositions = getEndPositions(data);
        drawEndPositions(endPositions);

        for (int i= 0; i< numShafts; i++) {
            AllenTubeComp tubeComp = mStick.getComp()[i + 1];
            AllenMAxisArc mAxis = tubeComp.getmAxisInfo();
            drawRadius(i, data.getShaftData().get(i).radius, shaftPositions.get(i), mAxis.getmTangent()[26]);
        }
        for (int i=0; i<jucPositions.size(); i++){
            drawRadius(i, data.getJunctionData().get(i).getRadius(), jucPositions.get(i), CoordinateConverter.sphericalToVector(new CoordinateConverter.SphericalCoordinates(1, data.getJunctionData().get(i).getAngleBisectorDirection())));
        }
        for (int i=0; i<endPositions.size(); i++){
            drawRadius(i, data.getTerminationData().get(i).getRadius(), endPositions.get(i), CoordinateConverter.sphericalToVector(new CoordinateConverter.SphericalCoordinates(1, data.getTerminationData().get(i).getDirection())));
        }
    }

    private void drawEndPositions(List<Point3d> endPositions) {
        for (int i = 0; i< endPositions.size(); i++) {
            drawPoint(endPositions.get(i), COMP_COLORS.get(i), 5f);
        }
    }

    private List<Point3d> getEndPositions(AllenMStickData data) {
        List<Point3d> endPositions = new LinkedList<>();
        for (TerminationData endData: data.getTerminationData()){
            Point3d position = convertPolarCoords(endData.getAngularPosition(), endData.getRadialPosition());
            endPositions.add(position);
        }
        return endPositions;
    }

    private void drawJuncPositions(List<Point3d> juncPositions) {
        for (int i = 0; i< juncPositions.size(); i++) {
            drawPoint(juncPositions.get(i), JUNC_COLORS.get(i), 5f);
        }
    }

    private List<Point3d> getJuncPositions(AllenMStickData data) {
        List<Point3d> jucPositions = new LinkedList<>();
        for (JunctionData jucData: data.getJunctionData()){
            Point3d position = convertPolarCoords(jucData.getAngularPosition(), jucData.getRadialPosition());
            jucPositions.add(position);
        }
        return jucPositions;
    }

    private void drawShaftPositions(int numShafts, List<Point3d> shaftPositions) {
        for (int i = 0; i< numShafts; i++) {
            drawPoint(shaftPositions.get(i), COMP_COLORS.get(i), 5f);
        }
    }

    private static List<Point3d> getShaftPositions(AllenMStickData data) {
        int numShafts = data.getShaftData().size();
        List<Point3d> shaftPositions = new LinkedList<>();
        for (int i = 0; i< numShafts; i++) {
            ShaftData shaftData = data.getShaftData().get(i);
            Point3d position = convertPolarCoords(shaftData.angularPosition, shaftData.radialPosition);
            shaftPositions.add(position);
        }
        return shaftPositions;
    }

    private void testShaftLength(int i, ShaftData shaftData) {
        double length = shaftData.length;
//           Point3d startPoint = new Point3d(-50,-50 - i*10,0);
        Point3d startPoint = new Point3d(-5,-25 + (i *5),-10);
        List<Point3d> shaftLengthLine = CoordinateConverter.vectorToLine(
                new Vector3d(length, 0, 0), 50, startPoint);
        drawLine(shaftLengthLine, COMP_COLORS.get(i));
    }

    private static Point3d convertPolarCoords(AngularCoordinates angularPosition, double radialPosition) {
        // Calculate the position using spherical coordinates
        Vector3d shaftAxis = CoordinateConverter.sphericalToVector(new CoordinateConverter.SphericalCoordinates(radialPosition, angularPosition));

        // Convert Vector3d to Point3d for drawing
        Point3d position = new Point3d(shaftAxis.x, shaftAxis.y, shaftAxis.z);
        return position;
    }



    private void drawPoint(Point3d position, RGBColor rgbColor, final float size) {
        window.draw(new Drawable() {
            @Override
            public void draw() {
                GL11.glPointSize(size);  // Set the size of the point
                GL11.glBegin(GL11.GL_POINTS);
                GL11.glColor3f(rgbColor.getRed(), rgbColor.getGreen(), rgbColor.getBlue());
                GL11.glVertex3d(position.x, position.y, position.z);
                GL11.glEnd();
            }
        });
    }


    private void testShaftOrientation(int i, ShaftData shaftData) {
        Vector3d orientation = CoordinateConverter.sphericalToVector(5, shaftData.orientation);
        Point3d startPoint = CoordinateConverter.sphericalToPoint(shaftData.radialPosition, shaftData.angularPosition);
        List<Point3d> tangentLine = CoordinateConverter.vectorToLine(orientation, 50, startPoint);
        raiseLine(tangentLine);
        drawLine(tangentLine, new RGBColor(1,0,1));
    }

    private void testShaftCurvature(ShaftData shaftData, AllenMAxisArc mAxis, int i) {
        double curvature = shaftData.curvature;
        double length = shaftData.length;

        double curvatureRadius = 1/curvature;
        double angleExtend = length/curvatureRadius;

        AllenMAxisArc mAxisArc = new AllenMAxisArc();
        mAxisArc.genArc(curvatureRadius, length);
        mAxisArc.transRotMAxis(mAxis.getTransRotHis_alignedPt(), mAxisArc.getTransRotHis_finalPos(), mAxisArc.getTransRotHis_rotCenter(), mAxisArc.getTransRotHis_finalTangent(), mAxisArc.getTransRotHis_devAngle());
        List<Point3d> line = Arrays.asList(mAxis.getmPts());
        line = line.subList(1,51);
        for (Point3d point:line){
            point.add(new Point3d(20,0,0));
        }
        drawLine(line, COMP_COLORS.get(i));
    }


    private void drawRadius(int i, double radius, Point3d startPoint, Vector3d tangent) {
        Vector3d normal = new Vector3d();
        normal.cross(tangent, new Vector3d(1,0,0));
        List<Point3d> disk = new LinkedList<>();
        for (double rot_degree=0; rot_degree < 2* Math.PI; rot_degree+=Math.PI/100){
            Vector3d nextDiskPoint = stickMath_lib.rotVecArAxis(normal, tangent, rot_degree);
            nextDiskPoint.normalize();
            nextDiskPoint.scale(radius);
            nextDiskPoint.add(startPoint);
            disk.add(new Point3d(nextDiskPoint.x, nextDiskPoint.y, nextDiskPoint.z));
        }

        drawLine(disk, COMP_COLORS.get(i));

    }

    private void raiseLine(List<Point3d> line) {
        for(Point3d point: line){
            //point.set(new Point3d(deg2mm(point.x), deg2mm(point.y), deg2mm(point.z)+50));
            point.set(new Point3d(point.x, point.y, point.z));
        }
    }


    private void drawLine(List<Point3d> line, RGBColor rgbColor){
        Drawable drawable;
        window.draw(drawable = new Drawable() {
            @Override
            public void draw() {
                int i;
                GL11.glLineWidth(2);
                GL11.glBegin(GL11.GL_LINE_STRIP);
                for (i=0; i<line.size(); i++)
                {
                    GL11.glColor3f( rgbColor.getRed(),  rgbColor.getGreen(),  rgbColor.getBlue());
                    //GL11.glVertex3d(mPts[i].getX(), mPts[i].getY(), mPts[i].getZ());
                    GL11.glVertex3d( line.get(i).x, line.get(i).y, line.get(i).z);
                }

                GL11.glEnd();
            }
        });
    }

    public void drawMassCenter(AllenMStickData data) {

        Point3d objCenter = data.getMassCenter();
        drawPoint(objCenter, new RGBColor(1,1,0), 5f);

    }
}