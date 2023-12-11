package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.Dependency;

import javax.sql.DataSource;

public class NAFCTrialParamDbUtil {
    @Dependency
    DataSource dataSource;

    public String readTrialParams(long tstamp) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        String sqlQuery = "SELECT xml FROM NAFCTrialParams WHERE tstamp = ?";
        return (String) jt.queryForObject(sqlQuery, new Object[]{tstamp}, String.class);
    }

    public void writeTrialParams(long tstamp, String xml) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("INSERT INTO NAFCTrialParams (tstamp, xml) VALUES (?, ?)",
                new Object[]{tstamp, xml});
    }

    public String readLatestTrialParams() {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        String sqlQuery = "SELECT xml FROM NAFCTrialParams WHERE tstamp = (SELECT MAX(tstamp) FROM NAFCTrialParams)";
        return (String) jt.queryForObject(sqlQuery, String.class);
    }

    public DataSource getDataSource() {
        return dataSource;
    }

    public void setDataSource(DataSource dataSource) {
        this.dataSource = dataSource;
    }
}