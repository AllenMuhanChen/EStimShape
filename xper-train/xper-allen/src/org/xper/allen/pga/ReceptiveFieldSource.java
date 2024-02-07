package org.xper.allen.pga;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.Dependency;
import org.xper.allen.drawing.ga.ConcaveHullReceptiveField;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.RFInfo;
import org.xper.rfplot.V4RFInfo;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;

public class ReceptiveFieldSource {

    @Dependency
    DataSource dataSource;

    public ReceptiveFieldSource() {
    }

    public ReceptiveField getReceptiveField() {
        long tstamp = readMaxTstampFromRFInfo();
        RFInfo rfInfo = readRFInfo(tstamp);
        return new ConcaveHullReceptiveField(rfInfo.getOutline());
    }

    public Coordinates2D getRFCenter(){
        long tstamp = readMaxTstampFromRFInfo();
        RFInfo rfInfo = readRFInfo(tstamp);
        return rfInfo.getCenter();
    }

    private RFInfo readRFInfo(long tstamp) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        String sql = "SELECT info FROM RFInfo WHERE tstamp = ?";

        // Query and map the result to RFInfo object
        V4RFInfo rfInfo = (V4RFInfo) jt.queryForObject(
                sql,
                new Object[]{tstamp},
                new RowMapper() {
                    public V4RFInfo mapRow(ResultSet rs, int rowNum) throws SQLException {
                        String xmlData = rs.getString("info");
                        try {
                            return V4RFInfo.fromXml(xmlData);
                        } catch (Exception e) {
                            throw new SQLException("Error deserializing RFInfo XML", e);
                        }
                    }
                });

        return rfInfo;
    }

    private Long readMaxTstampFromRFInfo() {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        String sql = "SELECT MAX(tstamp) FROM RFInfo";

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
}