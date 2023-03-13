package org.xper.allen.ga;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.xper.Dependency;
import org.xper.util.DbUtil;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

/**
 * Interacts with LineageGaInfo table
 */
public class LineageGaInfoDbUtil extends DbUtil {

    @Dependency
    protected DataSource dataSource;

    public LineageGaInfo readLineageGaInfo(long lineageId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        LineageGaInfo lineageGaInfo = new LineageGaInfo();
        jt.query("SELECT * FROM LineageGaInfo WHERE lineageId = ?",
                new Object[]{lineageId},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        lineageGaInfo.lineageId = rs.getLong("lineageId");
                        lineageGaInfo.treeSpec = rs.getString("treeSpec");
                        lineageGaInfo.regimeScore = rs.getDouble("regimeScore");
                    }});
        return lineageGaInfo;
    }

    public void writeLineageGaInfo(LineageGaInfo lineageGaInfo) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("INSERT INTO LineageGaInfo (lineageId, treeSpec, regimeScore) VALUES (?, ?, ?)",
                new Object[] {
                lineageGaInfo.lineageId,
                lineageGaInfo.treeSpec,
                lineageGaInfo.regimeScore
                });
    }

    public Double readRegimeScore(long lineageId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        List<Double> regimeScore = new ArrayList<>();
        jt.query("SELECT regimeScore FROM LineageGaInfo WHERE lineageId = ?",
                new Object[]{lineageId},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        regimeScore.add(rs.getDouble("regimeScore"));
                    }});
        if (regimeScore.size() == 0) {
            throw new RuntimeException("No regime score found for lineageId " + lineageId);
        }
        else if (regimeScore.size() > 1) {
            throw new RuntimeException("Multiple regime scores found for lineageId " + lineageId);
        }
        else {
            return regimeScore.get(0);
        }
    }

    public void updateRegimeScore(long lineageId, double regimeScore) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("UPDATE LineageGaInfo SET regimeScore = ? WHERE lineageId = ?",
                new Object[] {
                        regimeScore,
                        lineageId
                });
    }

    public String readTreeSpec(long lineageId) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        List<String> treeSpec = new ArrayList<>();
        jt.query("SELECT treeSpec FROM LineageGaInfo WHERE lineageId = ?",
                new Object[]{lineageId},
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        treeSpec.add(rs.getString("treeSpec"));
                    }});
        if (treeSpec.size() == 0) {
            throw new RuntimeException("No tree spec found for lineageId " + lineageId);
        }
        else if (treeSpec.size() > 1) {
            throw new RuntimeException("Multiple tree specs found for lineageId " + lineageId);
        }
        else {
            return treeSpec.get(0);
        }
    }

    public void updateTreeSpec(long lineageId, String treeSpec) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("UPDATE LineageGaInfo SET treeSpec = ? WHERE lineageId = ?",
                new Object[] {
                        treeSpec,
                        lineageId
                });
    }

    public DataSource getDataSource() {
        return dataSource;
    }

    public void setDataSource(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    public static class LineageGaInfo {
        Long lineageId;
        String treeSpec;
        Double regimeScore;
    }
}