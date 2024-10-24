package org.xper.allen.drawing.composition;
import com.mchange.v2.c3p0.ComboPooledDataSource;
import org.junit.Before;
import org.junit.After;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.util.CoordinateConverter;
import org.xper.allen.util.CoordinateConverter.SphericalCoordinates;
import org.xper.drawing.RGBColor;
import org.xper.drawing.stick.JuncPt_struct;
import org.xper.drawing.TestDrawingWindow;


import org.xper.drawing.stick.stickMath_lib;
import org.xper.util.ResourceUtil;

import javax.vecmath.Vector3d;
import javax.vecmath.Point3d;

import java.beans.PropertyVetoException;
import java.io.File;
import java.nio.file.Paths;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.*;

import static org.junit.Assert.assertTrue;

public class AllenMStickDataTest {
    private TestDrawingWindow window;

    private static final LinkedHashMap<Integer, RGBColor> COMP_COLORS = new LinkedHashMap<>();
    static {
        COMP_COLORS.put(1, new RGBColor(0,1,0));
        COMP_COLORS.put(2, new RGBColor(0,0,1));
        COMP_COLORS.put(3, new RGBColor(1,1,0));
        COMP_COLORS.put(4, new RGBColor(0,1,1));
        COMP_COLORS.put(5, new RGBColor(1,0,1));
        COMP_COLORS.put(6, new RGBColor(1,1,1));
        COMP_COLORS.put(0, new RGBColor(1,0,0));
    }

    private List<Drawable> drawables;
    private AllenMStickData data;

    private AllenMatchStick matchStick;
    private final static String FILE_NAME = Paths.get(ResourceUtil.getResource("testBin"), "AllenMStickDataTest_testFile").toString();;

    @Before
    public void setUp() throws Exception {
        drawables = new LinkedList<>();
        setMStickData();
        getTestDrawingWindow();
    }

    @After
    public void tearDown() throws Exception {
        window.close();
    }

    @Test
    public void testExport(){
        System.out.println(data.toXml());
        data.writeInfo2File(FILE_NAME);
        File testFile = new File(FILE_NAME +"_spec.xml");
        assertTrue(testFile.exists());
//        testFile.delete();
    }

    @Test
    public void testShaftData() {
        drawMStick(matchStick);

        //SHAFTS
        int numShafts = data.getShaftData().size();
        for (int i = 0; i< numShafts; i++) {
            ShaftData shaftData = data.getShaftData().get(i);
            AllenTubeComp tubeComp = matchStick.getComp()[i + 1];
            AllenMAxisArc mAxis = tubeComp.getmAxisInfo();

            testShaftLength(i, shaftData);
            testSphericalPosition(matchStick, i, shaftData.angularPosition, shaftData.radialPosition);
            testShaftOrientation(i, shaftData);
            testRadius(i, shaftData.radius, mAxis.getmPts()[26], mAxis.getmTangent()[26]);
            testShaftCurvature(shaftData, mAxis, i);
        }

        window.animateRotation(drawables, 1, 10000);
    }

    private void setMStickData() {
        matchStick = new AllenMatchStick();
        matchStick.setProperties(5, "SHADE");
        matchStick.genMatchStickRand();

        data = matchStick.getMStickData();
    }

    @Test
    public void testTerminationData(){
        drawMStick(matchStick);

        int numTerminations = data.getTerminationData().size();
        for (int i=0; i<numTerminations; i++){
            TerminationData terminationData = data.terminationData.get(i);
            testSphericalPosition(matchStick, i, terminationData.angularPosition, terminationData.radialPosition);
            testTerminationOrientation(i, terminationData);
            testTerminationRadius(i, terminationData);
        }

        window.animateRotation(drawables, 1, 10000);
    }

    @Test
    public void testJunctionData(){
        AllenMatchStick matchStick = new AllenMatchStick();
        matchStick.setProperties(5, "SHADE");
        matchStick.genMatchStickRand();

        AllenMStickData data = matchStick.getMStickData();
        drawMStick(matchStick);

        int numJunctions = data.getJunctionData().size();
        for (int i=0; i<numJunctions; i++){
            JunctionData junctionData = data.junctionData.get(i);
            JuncPt_struct juncPt_struct = matchStick.getJuncPt()[i + 1];

            testSphericalPosition(matchStick, i, junctionData.angularPosition, junctionData.radialPosition);
            testJunctionBisector(junctionData, juncPt_struct);

        }
        window.animateRotation(drawables, 1, 10000);
    }

    private void testJunctionBisector(JunctionData junctionData, JuncPt_struct juncPt_struct) {
            Vector3d angleBisector = CoordinateConverter.sphericalToVector(20, junctionData.getAngleBisectorDirection());
            Point3d juncLocation = CoordinateConverter.sphericalToPoint(junctionData.getRadialPosition(), junctionData.getAngularPosition());
            List<Point3d> angleBisectorLine = CoordinateConverter.vectorToLine(angleBisector, 50, juncLocation);
            drawLine(angleBisectorLine, new RGBColor(0,1,0));

            Vector3d bisectedVector1 = juncPt_struct.getTangent()[1];
            bisectedVector1.scale(10);
            List<Point3d> bisectedLine1 = CoordinateConverter.vectorToLine(bisectedVector1, 50, juncLocation);
            drawLine(bisectedLine1, new RGBColor(0,1,0));

            Vector3d bisectedVector2 = juncPt_struct.getTangent()[2];
            bisectedVector2.scale(10);
            List<Point3d> bisectedLine2 = CoordinateConverter.vectorToLine(bisectedVector2, 50, juncLocation);
            drawLine(bisectedLine2, new RGBColor(0,1,0));
    }

    private void testTerminationRadius(int i, TerminationData terminationData) {
        Point3d startPoint = CoordinateConverter.sphericalToPoint(terminationData.getRadialPosition(), terminationData.getAngularPosition());
        Vector3d orientation = CoordinateConverter.sphericalToVector(1, terminationData.direction);
        testRadius(i, terminationData.radius, startPoint, orientation);
    }

    private void testTerminationOrientation(int i, TerminationData terminationData) {
        Vector3d tangent = CoordinateConverter.sphericalToVector(10, terminationData.direction);
        Point3d endPtPosition = CoordinateConverter.sphericalToPoint(terminationData.getRadialPosition(), terminationData.angularPosition);
        drawLine(CoordinateConverter.vectorToLine(tangent, 50, endPtPosition), COMP_COLORS.get(i));
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

    private void testRadius(int i, double radius, Point3d startPoint, Vector3d tangent) {
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

    private void testShaftOrientation(int i, ShaftData shaftData) {
        Vector3d orientation = CoordinateConverter.sphericalToVector(5, shaftData.orientation);
        Point3d startPoint = CoordinateConverter.sphericalToPoint(shaftData.radialPosition, shaftData.angularPosition);
        List<Point3d> tangentLine = CoordinateConverter.vectorToLine(orientation, 50, startPoint);
        raiseLine(tangentLine);
        drawLine(tangentLine, new RGBColor(1,0,1));
    }

    private void testShaftLength(int i, ShaftData shaftData) {
        double length = shaftData.length;
//           Point3d startPoint = new Point3d(-50,-50 - i*10,0);
        Point3d startPoint = new Point3d(-5,-25 + (i *5),-10);
        List<Point3d> shaftLengthLine = CoordinateConverter.vectorToLine(new Vector3d(length, 0, 0), 50, startPoint);
        raiseLine(shaftLengthLine);
        drawLine(shaftLengthLine, COMP_COLORS.get(i));
    }

    private void testSphericalPosition(AllenMatchStick matchStick, int i, AngularCoordinates angularPosition, double radialPosition) {

        Point3d massCenter = matchStick.getMassCenter();

        Vector3d shaftAxis = CoordinateConverter.sphericalToVector(new SphericalCoordinates(radialPosition, angularPosition));
        List<Point3d> shaftLine = CoordinateConverter.vectorToLine(shaftAxis, 100, massCenter);

        raiseLine(shaftLine);
        drawLine(shaftLine, COMP_COLORS.get(i));
    }

    private void raiseLine(List<Point3d> line) {
        for(Point3d point: line){
            //point.set(new Point3d(deg2mm(point.x), deg2mm(point.y), deg2mm(point.z)+50));
            point.set(new Point3d(point.x, point.y, point.z));
        }
    }


    private void getTestDrawingWindow() {
        window = TestDrawingWindow.createDrawerWindow(500, 500);
    }


    private void drawMStick(AllenMatchStick mStick){
        Drawable drawable;
        window.draw(drawable = new Drawable() {
            @Override
            public void draw() {mStick.drawGhost();
            }
        });
        drawables.add(drawable);
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
        drawables.add(drawable);
    }

    private void drawLine(List<Point3d> line, RGBColor rgbColor, float alpha){
        Drawable drawable;
        window.draw(drawable = new Drawable() {
            @Override
            public void draw() {
                int i;
                GL11.glLineWidth(2);
                GL11.glBegin(GL11.GL_LINE_STRIP);
                for (i=0; i<line.size(); i++)
                {
                    float scalar = (float)(line.size()/2+i)/((float)line.size()/2 + line.size());
                    GL11.glColor4f(scalar*rgbColor.getRed(), scalar*rgbColor.getGreen(), scalar*rgbColor.getBlue(), alpha);
                    //GL11.glVertex3d(mPts[i].getX(), mPts[i].getY(), mPts[i].getZ());
                    GL11.glVertex3d( line.get(i).x, line.get(i).y, line.get(i).z);
                }

                GL11.glEnd();
            }
        });
        drawables.add(drawable);
    }

    @Test
    public void reloadData(){
        String specPath = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/specs";
        ComboPooledDataSource dataSource = getComboPooledDataSource();

        List<Long> stimSpecIds = fetchAllStimSpecIds(dataSource);

        int i = 0;
        for (Long stimId: stimSpecIds){
            AllenMStickData reloadedData = reloadMStickData(specPath, stimId);
            updateDataForId(dataSource, stimId, "data", reloadedData.toXml());
            System.out.println("Finished " + i + " of " + stimSpecIds.size() + " stimSpecs");
            i++;
        }
    }

    @Test
    public void reloadOneData(){
        String specPath = "/home/r2_allen/Documents/EStimShape/ga_dev_240207/specs";
        ComboPooledDataSource dataSource = getComboPooledDataSource();

        long stimId = fetchAllStimSpecIds(dataSource).get(1);
        AllenMStickData reloadedData = reloadMStickData(specPath, stimId);
        System.out.println(reloadedData.toXml());
    }

    private static ComboPooledDataSource getComboPooledDataSource() {
        ComboPooledDataSource dataSource = new ComboPooledDataSource();
        try {
            dataSource.setDriverClass("com.mysql.jdbc.Driver");
        } catch (PropertyVetoException e) {
            throw new RuntimeException(e);
        }
        dataSource.setJdbcUrl("jdbc:mysql://172.30.6.80/allen_estimshape_ga_dev_240207?rewriteBatchedStatements=true");
        dataSource.setUser("xper_rw");
        dataSource.setPassword("up2nite");
        return dataSource;
    }

    private static List<Long> fetchAllStimSpecIds(ComboPooledDataSource dataSource) {
        String query = "SELECT id FROM StimSpec";
        List<Long> stimSpecIds = new ArrayList<>();
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(query);
             ResultSet rs = stmt.executeQuery()) {

            while (rs.next()) {
                long id = rs.getLong("id");
                stimSpecIds.add(id); // Add each ID to the list
            }
        } catch (SQLException e) {
            e.printStackTrace();
            // Handle database access errors here
        }
        return stimSpecIds;
    }

    private static AllenMStickData reloadMStickData(String specPath, long stimId) {
        String mStickSpecPath = specPath + "/" + Long.toString(stimId) + "_spec.xml";
        AllenMatchStick mStick = new AllenMatchStick();
        mStick.genMatchStickFromFile(mStickSpecPath);

        AllenMStickData reloadedData = mStick.getMStickData();
        return reloadedData;
    }

    private static void updateDataForId(ComboPooledDataSource dataSource, long id, String columnName, String newValue) {
        String query = "UPDATE StimSpec SET " + columnName + " = ? WHERE id = ?";
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(query)) {
            stmt.setString(1, newValue);
            stmt.setLong(2, id);

            int affectedRows = stmt.executeUpdate();
            if (affectedRows > 0) {
                System.out.println("Update successful for ID: " + id);
            } else {
                System.out.println("Update failed for ID: " + id + ". No rows affected.");
            }
        } catch (SQLException e) {
            e.printStackTrace();
            // Handle database access errors here
        }
    }

}