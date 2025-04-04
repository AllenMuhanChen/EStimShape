package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;

import java.sql.ResultSet;
import java.sql.SQLException;

public class ContrastPropertyManager extends StimPropertyManager<Double> {
    private static final String TABLE_NAME = "StimContrast";

    public ContrastPropertyManager(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);
    }

    @Override
    public void createTableIfNotExists() {
        jdbcTemplate.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE_NAME + " (" +
                        "stim_id BIGINT PRIMARY KEY, " +
                        "contrast FLOAT NOT NULL)"
        );
    }

    @Override
    public void writeProperty(Long stimId, Double contrast) {
        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, contrast) " +
                        "VALUES (?, ?) " +
                        "ON DUPLICATE KEY UPDATE contrast = ?",
                new Object[]{stimId, contrast, contrast}
        );
    }

    @Override
    public Double readProperty(Long stimId) {
        return (Double) jdbcTemplate.queryForObject(
                "SELECT contrast FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        return rs.getDouble("contrast");
                    }
                }
        );
    }

    @Override
    public String getTableName() {
        return TABLE_NAME;
    }
}