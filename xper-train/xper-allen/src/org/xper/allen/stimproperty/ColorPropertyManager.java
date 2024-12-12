package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.drawing.RGBColor;

import java.sql.ResultSet;
import java.sql.SQLException;

public class ColorPropertyManager extends StimPropertyManager<RGBColor> {
    private static final String TABLE_NAME = "StimColor";

    public ColorPropertyManager(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);

    }

    @Override
    public void createTableIfNotExists() {
        jdbcTemplate.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE_NAME + " (" +
                        "stim_id BIGINT PRIMARY KEY, " +
                        "red FLOAT NOT NULL, " +
                        "green FLOAT NOT NULL, " +
                        "blue FLOAT NOT NULL)"
        );
    }

    @Override
    public void writeProperty(Long stimId, RGBColor color) {
        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, red, green, blue) " +
                        "VALUES (?, ?, ?, ?) " +
                        "ON DUPLICATE KEY UPDATE red = ?, green = ?, blue = ?",
                new Object[]{stimId, color.getRed(), color.getGreen(), color.getBlue(),
                        color.getRed(), color.getGreen(), color.getBlue()}
        );
    }

    @Override
    public RGBColor readProperty(Long stimId) {
        return (RGBColor) jdbcTemplate.queryForObject(
                "SELECT red, green, blue FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        return new RGBColor(
                                rs.getFloat("red"),
                                rs.getFloat("green"),
                                rs.getFloat("blue")
                        );
                    }
                }
        );
    }

    @Override
    public String getTableName() {
        return TABLE_NAME;
    }
}