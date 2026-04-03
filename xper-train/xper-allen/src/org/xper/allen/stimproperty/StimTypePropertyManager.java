package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.allen.pga.StimType;
import java.sql.ResultSet;
import java.sql.SQLException;

public class StimTypePropertyManager extends StimPropertyManager<StimType> {
    private static final String TABLE_NAME = "StimGaInfo";

    public StimTypePropertyManager(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);
    }

    @Override
    public void createTableIfNotExists() {
        // StimGaInfo table is always present; no need to create
    }

    @Override
    public void writeProperty(Long stimId, StimType stimType) {
        // Don't write
    }

    @Override
    public StimType readProperty(Long stimId) {
        return (StimType) jdbcTemplate.queryForObject(
                "SELECT stim_type FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        return StimType.valueOf(rs.getString("stim_type"));
                    }
                }
        );
    }

    @Override
    public String getTableName() {
        return TABLE_NAME;
    }
}