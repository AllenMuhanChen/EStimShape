package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import java.sql.ResultSet;
import java.sql.SQLException;

public class SizePropertyManager extends StimPropertyManager<Float> {
    private static final String TABLE_NAME = "StimSize";

    public SizePropertyManager(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);
    }

    @Override
    public void createTableIfNotExists() {
        jdbcTemplate.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE_NAME + " (" +
                        "stim_id BIGINT PRIMARY KEY, " +
                        "size FLOAT NOT NULL)"
        );
    }

    public void writeProperty(Long stimId, Float size) {
        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, size) " +
                        "VALUES (?, ?) " +
                        "ON DUPLICATE KEY UPDATE size = ?",
                new Object[]{stimId, size, size}
        );
    }

    @Override
    public void writeProperty(Long stimId) {
        throw new UnsupportedOperationException("Must provide size value when writing");
    }

    @Override
    public Float readProperty(Long stimId) {
        return (Float) jdbcTemplate.queryForObject(
                "SELECT size FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        return rs.getFloat("size");
                    }
                }
        );
    }

    @Override
    public String getTableName() {
        return TABLE_NAME;
    }
}