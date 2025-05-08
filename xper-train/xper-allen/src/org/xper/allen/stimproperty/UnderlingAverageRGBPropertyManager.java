package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.drawing.RGBColor;

import java.sql.ResultSet;
import java.sql.SQLException;

public class UnderlingAverageRGBPropertyManager extends StimPropertyManager<RGBColor> {
    private static final String TABLE_NAME = "UnderlyingAverageRGB";

    public UnderlingAverageRGBPropertyManager(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);
    }

    @Override
    public void createTableIfNotExists() {
        jdbcTemplate.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE_NAME + " (" +
                        "stim_id BIGINT PRIMARY KEY, " +
                        "average_rgb VARCHAR(50) NOT NULL)"
        );
    }

    @Override
    public void writeProperty(Long stimId, RGBColor averageRGB) {
        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, average_rgb) " +
                        "VALUES (?, ?) " +
                        "ON DUPLICATE KEY UPDATE average_rgb = ?",
                new Object[]{stimId, averageRGB.toString(), averageRGB.toString()}
        );
    }

    @Override
    public RGBColor readProperty(Long stimId) {
        return (RGBColor) jdbcTemplate.queryForObject(
                "SELECT average_rgb FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
                new RowMapper() {
                    public RGBColor mapRow(ResultSet rs, int rowNum) throws SQLException {
                        return RGBColor.fromString(rs.getString("average_rgb"));
                    }
                }
        );
    }

    @Override
    public String getTableName() {
        return TABLE_NAME;
    }
}