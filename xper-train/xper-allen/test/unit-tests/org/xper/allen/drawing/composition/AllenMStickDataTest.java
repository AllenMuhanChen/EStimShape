package org.xper.allen.drawing.composition;
import com.mchange.v2.c3p0.ComboPooledDataSource;
import org.junit.Before;
import org.junit.After;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.experiment.EStimShapeProceduralMatchStick;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.allen.util.CoordinateConverter;
import org.xper.allen.util.CoordinateConverter.SphericalCoordinates;
import org.xper.drawing.RGBColor;
import org.xper.drawing.stick.JuncPt_struct;
import org.xper.drawing.TestDrawingWindow;

import org.xper.util.ResourceUtil;

import javax.vecmath.Vector3d;
import javax.vecmath.Point3d;

import java.beans.PropertyVetoException;
import java.nio.file.Paths;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.*;

import static org.junit.Assert.assertTrue;
import static org.xper.allen.drawing.ga.GAMatchStickTest.COMPLETE_RF;
import static org.xper.allen.drawing.ga.GAMatchStickTest.PARTIAL_RF;

public class AllenMStickDataTest {
    private TestDrawingWindow window;

    private static final LinkedHashMap<Integer, RGBColor> COMP_COLORS = new LinkedHashMap<>();
    static {
        COMP_COLORS.put(0, new RGBColor(1,0,0));
        COMP_COLORS.put(1, new RGBColor(0,1,0));
        COMP_COLORS.put(2, new RGBColor(0,0,1));
        COMP_COLORS.put(3, new RGBColor(1,1,0));
        COMP_COLORS.put(4, new RGBColor(0,1,1));
        COMP_COLORS.put(5, new RGBColor(1,0,1));
    }

    private List<Drawable> drawables;
    private AllenMStickData data;

    private AllenMatchStick matchStick;
    public final static String FILE_NAME = Paths.get(ResourceUtil.getResource("testBin"), "AllenMStickDataTest_testFile").toString();;
    private ReceptiveField receptiveField;
    private GaussianNoiseMapper noiseMapper;


    private void setMStickData() {
        String stimType = "Growing";
        RFStrategy rfStrategy = RFStrategy.PARTIALLY_INSIDE;

        if (rfStrategy == RFStrategy.COMPLETELY_INSIDE){
            receptiveField = COMPLETE_RF;
        } else {
            receptiveField = PARTIAL_RF;
        }

        GAMatchStick parentStick = new GAMatchStick(receptiveField, rfStrategy);
        parentStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 2), "SHADE", 1.0);
        parentStick.genMatchStickRand();
        AllenMStickSpec parentSpec = new AllenMStickSpec();
        parentSpec.setMStickInfo(parentStick, true);
        parentSpec.writeInfo2File(FILE_NAME);

        switch (stimType){
            case "EStimShapeProceduralRand":
                matchStick = new EStimShapeProceduralMatchStick(rfStrategy, receptiveField, noiseMapper);
                matchStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 1.5), "SHADE", 1.0);
                matchStick.genMatchStickRand();
                break;
            case "EStimShapeProcedural":
                EStimShapeProceduralMatchStick baseMStick = new EStimShapeProceduralMatchStick(rfStrategy, receptiveField, noiseMapper);
                baseMStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 1.5), "SHADE", 1.0);
                baseMStick.genMatchStickRand();
                baseMStick.setMaxAttempts(-1);

                matchStick = new EStimShapeProceduralMatchStick(rfStrategy, receptiveField, noiseMapper);
                matchStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 1.5), "SHADE", 1.0);
                ((EStimShapeProceduralMatchStick) matchStick).genMatchStickFromComponentInNoise(baseMStick, baseMStick.chooseRandLeaf(),
                        4, true, -1);
                break;
            case "Seeding":
                matchStick = new GAMatchStick(receptiveField, rfStrategy);
                matchStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 1.5), "SHADE", 1.0);
                matchStick.genMatchStickRand();
                break;
            case "Zooming":
                matchStick = new GAMatchStick(PARTIAL_RF, RFStrategy.PARTIALLY_INSIDE);
                matchStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, 1.5), "SHADE", 1.0);
                ((GAMatchStick) matchStick).genPartialFromFile(FILE_NAME + "_spec.xml", 1);
                break;
            case "Growing":
                matchStick = new GrowingMatchStick(receptiveField, 1/3.0, rfStrategy, "SHADE");
                matchStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 1.5), "SHADE", 1.0);
                ((GrowingMatchStick) matchStick).genGrowingMatchStick(parentStick, 0.5);
                break;
            case "AddLimbs":
                matchStick = new GAMatchStick(receptiveField, rfStrategy);
                matchStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 1.5), "SHADE", 1.0);
                ((GrowingMatchStick) matchStick).genAddedLimbsMatchStick(parentStick, 1);
                break;
            case "RemoveLimbs":
                matchStick = new GAMatchStick(receptiveField, rfStrategy);
                matchStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, 1.5), "SHADE", 1.0);
                ((GrowingMatchStick) matchStick).genRemovedLimbsMatchStick(parentStick, new HashSet<>(Arrays.asList(1)));
                break;
            case "Rand":
                matchStick = new AllenMatchStick();
                matchStick.setProperties(5, "SHADE", 1.0);
                matchStick.genMatchStickRand();
        }




        data = (AllenMStickData) matchStick.getMStickData();
//        System.out.println(data.toXml());
    }

    @Before
    public void setUp() throws Exception {
        drawables = new LinkedList<>();

        noiseMapper = new GaussianNoiseMapper();
        noiseMapper.setBackground(0);
        noiseMapper.setWidth(1000);
        noiseMapper.setHeight(1000);

        setMStickData();
        getTestDrawingWindow();



    }

    @After
    public void tearDown() throws Exception {
        window.close();
    }


    @Test
    public void testShaftData() {
//        if (matchStick instanceof Thumbnailable){
//            drawThumbnail((GAMatchStick) matchStick);
//            ThreadUtil.sleep(1000);
//        }

        drawMStick(matchStick);

        //SHAFTS
        int numShafts = data.getShaftData().size();
        for (int i = 0; i< numShafts; i++) {
            ShaftData shaftData = data.getShaftData().get(i);
            AllenTubeComp tubeComp = matchStick.getComp()[i + 1];
            AllenMAxisArc mAxis = tubeComp.getmAxisInfo();

            testShaftLength(i, shaftData);
            testSphericalPosition(i, shaftData.angularPosition, shaftData.radialPosition);
            testShaftOrientation(i, shaftData);
            testShaftRadius(i, shaftData);
            testShaftCurvature(shaftData, mAxis, i);
        }

        window.animateRotation(drawables, 1, 10000);

    }

    @Test
    public void testTerminationData(){
        drawMStick(matchStick);

        int numTerminations = data.getTerminationData().size();
        for (int i=0; i<numTerminations; i++){
            TerminationData terminationData = data.terminationData.get(i);
            testSphericalPosition(i, terminationData.angularPosition, terminationData.radialPosition);
            testTerminationOrientation(i, terminationData);
            testTerminationRadius(i, terminationData);
        }


        window.animateRotation(drawables, 1, 10000);
    }

    @Test
    public void testJunctionData(){
        drawMStick(matchStick);


        for (int i=0; i<data.junctionData.size(); i++) {
            JunctionData junctionData = data.junctionData.get(i);
            JuncPt_struct juncPt_struct = matchStick.getJuncPt()[junctionData.getId()];

//            testSphericalPosition(i, junctionData.angularPosition, junctionData.radialPosition);
            testJunctionBisector(junctionData, juncPt_struct,junctionData.getConnectedCompIds().get(0), junctionData.getConnectedCompIds().get(1) );

        }


        window.animateRotation(drawables, 1, 10000);
    }


    private void testShaftRadius(int i, ShaftData shaftData) {
        Point3d massCenter = data.getMassCenter();
        Point3d shaftCenter = CoordinateConverter.sphericalToPoint(new SphericalCoordinates(shaftData.radialPosition, shaftData.angularPosition));
        shaftCenter.add(massCenter);

        double radius = shaftData.radius;
        Vector3d tangent = CoordinateConverter.sphericalToVector(1, shaftData.orientation);
        tangent.normalize();

        testRadius(i, tangent, radius, shaftCenter);
    }

    private void testRadius(int i, Vector3d tangent, double radius, Point3d ringCenter) {
        // 1. Create two vectors that define the plane of our disk
        // First basis vector - perpendicular to tangent
        Vector3d normalizedTangent = new Vector3d(tangent);
        normalizedTangent.normalize();

        Vector3d basis1 = new Vector3d();
        basis1.cross(normalizedTangent, new Vector3d(1,0,0));
        if (basis1.length() < 1e-6) {
            basis1.cross(normalizedTangent, new Vector3d(0,1,0));
        }
        basis1.normalize();

        // Second basis vector - also perpendicular to tangent
        Vector3d basis2 = new Vector3d();
        basis2.cross(normalizedTangent, basis1);
        basis2.normalize();

        // 2. Generate points around the circle
        List<Point3d> disk = new LinkedList<>();
        for (double theta = 0; theta < 2*Math.PI; theta += Math.PI/100) {
            // For each angle theta, compute position using:
            // point = center + radius * (basis1*cos(theta) + basis2*sin(theta))
            Vector3d circleVector = new Vector3d();
            circleVector.scaleAdd(Math.cos(theta), basis1,
                    new Vector3d(basis2.x * Math.sin(theta),
                            basis2.y * Math.sin(theta),
                            basis2.z * Math.sin(theta)));
            circleVector.scale(radius);

            Point3d diskPoint = new Point3d(ringCenter);
            diskPoint.add(circleVector);
            disk.add(diskPoint);
        }

        drawLine(disk, COMP_COLORS.get(i));
    }

    private void testShaftOrientation(int i, ShaftData shaftData) {
        Point3d massCenter = data.getMassCenter();
        Vector3d orientation = CoordinateConverter.sphericalToVector(5, shaftData.orientation);

        Point3d startPoint = CoordinateConverter.sphericalToPoint(shaftData.radialPosition, shaftData.angularPosition);
        startPoint.add(massCenter);

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

    private void testSphericalPosition(int i, AngularCoordinates angularPosition, double radialPosition) {

        Point3d massCenter = data.getMassCenter();

        Vector3d axis = CoordinateConverter.sphericalToVector(new SphericalCoordinates(radialPosition, angularPosition));
        List<Point3d> shaftLine = CoordinateConverter.vectorToLine(axis, 100, massCenter);

        raiseLine(shaftLine);
        drawLine(shaftLine, COMP_COLORS.get(i));
    }



//    private void setMStickData() {
//        matchStick = new AllenMatchStick();
//        matchStick.setProperties(5, "SHADE");
//        matchStick.genMatchStickRand();
//
//        data = (AllenMStickData) matchStick.getMStickData();
//    }


    private void testTerminationOrientation(int i, TerminationData terminationData) {
        Vector3d tangent = CoordinateConverter.sphericalToVector(10, terminationData.direction);
        Point3d endPtPosition = CoordinateConverter.sphericalToPoint(terminationData.getRadialPosition(), terminationData.angularPosition);
        endPtPosition.add(data.getMassCenter());
        drawLine(CoordinateConverter.vectorToLine(tangent, 50, endPtPosition), COMP_COLORS.get(i));
    }

    private void testTerminationRadius(int i, TerminationData terminationData) {
        Point3d startPoint = CoordinateConverter.sphericalToPoint(terminationData.getRadialPosition(), terminationData.getAngularPosition());
        Point3d massCenter = data.getMassCenter();
        startPoint.add(massCenter);
        Vector3d orientation = CoordinateConverter.sphericalToVector(1, terminationData.direction);
        testRadius(i, orientation, terminationData.radius, startPoint);
    }



    private void testJunctionBisector(JunctionData junctionData, JuncPt_struct juncPt_struct, int comp1, int comp2) {
            Vector3d angleBisector = CoordinateConverter.sphericalToVector(10, junctionData.getAngleBisectorDirection());
            Point3d juncLocation = CoordinateConverter.sphericalToPoint(junctionData.getRadialPosition(), junctionData.getAngularPosition());
            juncLocation.add(data.getMassCenter());

//            List<Point3d> angleBisectorLine = CoordinateConverter.vectorToLine(angleBisector, 50, juncLocation);
//            drawLine(angleBisectorLine, new RGBColor(1,1,0));

            Vector3d bisectedVector1 = juncPt_struct.getTangentOfOwner(comp1);
            bisectedVector1.normalize();
            bisectedVector1.scale(10);
            List<Point3d> bisectedLine1 = CoordinateConverter.vectorToLine(bisectedVector1, 50, juncLocation);
            drawLine(bisectedLine1, COMP_COLORS.get(comp1-1));

            Vector3d bisectedVector2 = juncPt_struct.getTangentOfOwner(comp2);
            bisectedVector2.normalize();
            bisectedVector2.scale(10);
            List<Point3d> bisectedLine2 = CoordinateConverter.vectorToLine(bisectedVector2, 50, juncLocation);
            drawLine(bisectedLine2, COMP_COLORS.get(comp2-1));
    }

    private void testShaftCurvature(ShaftData shaftData, AllenMAxisArc mAxis, int i) {
        double curvature = shaftData.curvature;
        double length = shaftData.length;

        double curvatureRadius = 1/curvature;

        AllenMAxisArc mAxisArc = new AllenMAxisArc();
        mAxisArc.genArc(curvatureRadius, length);
        Point3d transRotHisFinalPos = mAxis.getTransRotHis_finalPos();
        mAxisArc.transRotMAxis(mAxis.getTransRotHis_alignedPt(), transRotHisFinalPos, mAxis.getTransRotHis_rotCenter(), mAxis.getTransRotHis_finalTangent(), mAxis.getTransRotHis_devAngle());
        List<Point3d> line = Arrays.asList(mAxisArc.getmPts());
        line = line.subList(1,51);
        drawLine(line, COMP_COLORS.get(i));
    }



    private void raiseLine(List<Point3d> line) {
        for(Point3d point: line){
            //point.set(new Point3d(deg2mm(point.x), deg2mm(point.y), deg2mm(point.z)+50));
            point.set(new Point3d(point.x, point.y, point.z));
        }
    }


    private void getTestDrawingWindow() {
        window = TestDrawingWindow.createDrawerWindow(1000, 1000);
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

    private void drawThumbnail(GAMatchStick mStick){
        Drawable drawable;
        window.draw(drawable = new Drawable() {
            @Override
            public void draw() {mStick.drawThumbnail(window.renderer.getWidth(), window.renderer.getHeight());
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

        AllenMStickData reloadedData = (AllenMStickData) mStick.getMStickData();
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