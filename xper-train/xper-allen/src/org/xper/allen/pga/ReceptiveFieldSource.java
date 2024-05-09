package org.xper.allen.pga;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.Dependency;
import org.xper.allen.drawing.ga.ConcaveHullReceptiveField;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.rfplot.RFInfo;
import org.xper.rfplot.V4RFInfo;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

/**
 * Bridge between the database storage of RF info and xper use of it.
 * All RFInfo stored on database should be in degrees
 * All RFInfo use in xper should be in mm
 *
 * Therefore this class should convert all of the RFInfo from degrees to mm
 */
public class ReceptiveFieldSource {

    @Dependency
    DataSource dataSource;

    @Dependency
    AbstractRenderer renderer;

    public ReceptiveFieldSource() {
    }

    public ReceptiveField getReceptiveField() {
        long tstamp = readMaxTstampFromRFInfo();
        RFInfo rfInfo = readRFInfo(tstamp);
        List<Coordinates2D> outlineDegrees = rfInfo.getOutline();
        return new ConcaveHullReceptiveField(outlineDegrees, getRFCenterMm());
    }

    public Coordinates2D getRFCenterMm(){
        Coordinates2D rfCenterDegrees = getRFCenterDegrees();
        Coordinates2D rfCenterMm = new Coordinates2D(
                renderer.deg2mm(rfCenterDegrees.getX()),
                renderer.deg2mm(rfCenterDegrees.getY()));
        return rfCenterMm;
    }

    public Coordinates2D getRFCenterDegrees() {
        long tstamp = readMaxTstampFromRFInfo();
        RFInfo rfInfo = readRFInfo(tstamp);
        Coordinates2D rfCenterDegrees = rfInfo.getCenter();
        return rfCenterDegrees;
    }

    public double getRFRadiusMm(){
        double rfRadiusMm = renderer.deg2mm(getRFRadiusDegrees());
        return rfRadiusMm;
    }

    public double getRFRadiusDegrees(){
        long tstamp = readMaxTstampFromRFInfo();
        RFInfo rfInfo = readRFInfo(tstamp);
        double rfRadiusDegrees = rfInfo.getRadius();
        System.out.println("RF Radius in degrees: " + rfRadiusDegrees + " RF Radius in mm: " + renderer.deg2mm(rfRadiusDegrees));

        return rfRadiusDegrees;
    }

    public RGBColor getRFColor(){
        long tstamp = readMaxTstampFromRFInfo();
        V4RFInfo rfInfo = (V4RFInfo) readRFInfo(tstamp);
        return rfInfo.getColor();
    }


    private RFInfo readRFInfo(long tstamp) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        String sql = "SELECT info FROM RFInfo WHERE tstamp = ?";

        // Query and map the result to RFInfo object
        RFInfo rfInfo = (RFInfo) jt.queryForObject(
                sql,
                new Object[]{tstamp},
                new RowMapper() {
                    public RFInfo mapRow(ResultSet rs, int rowNum) throws SQLException {
                        String xmlData = rs.getString("info");
                        try {
                            return RFInfo.fromXml(xmlData);
                        } catch (Exception e) {
                            throw new SQLException("Error deserializing RFInfo XML", e);
                        }
                    }
                });

        return rfInfo;
    }

    private Long readMaxTstampFromRFInfo() {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        String sql = "SELECT MAX(tstamp) FROM RFInfo WHERE channel = 'SUPRA-000'";

        // Execute the query and return the result
        Long maxTstamp = (Long) jt.queryForObject(sql, Long.class);

        return maxTstamp;
    }

    public DataSource getDataSource() {
        return dataSource;
    }

    public void setDataSource(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    public AbstractRenderer getRenderer() {
        return renderer;
    }

    public void setRenderer(AbstractRenderer renderer) {
        this.renderer = renderer;
    }
}