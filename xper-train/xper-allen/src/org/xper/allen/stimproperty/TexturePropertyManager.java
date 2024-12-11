package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import java.sql.ResultSet;
import java.sql.SQLException;

public class TexturePropertyManager extends StimPropertyManager<String> {
    private static final String TABLE_NAME = "StimTexture";

    public TexturePropertyManager(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);
    }

    @Override
    public void createTableIfNotExists() {
        jdbcTemplate.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE_NAME + " (" +
                        "stim_id BIGINT PRIMARY KEY, " +
                        "texture_type VARCHAR(50) NOT NULL)"
        );
    }

    public void writeProperty(Long stimId, String textureType) {
        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, texture_type) " +
                        "VALUES (?, ?) " +
                        "ON DUPLICATE KEY UPDATE texture_type = ?",
                new Object[]{stimId, textureType, textureType}
        );
    }

    @Override
    public void writeProperty(Long stimId) {
        throw new UnsupportedOperationException("Must provide texture type when writing");
    }

    @Override
    public String readProperty(Long stimId) {
        return (String) jdbcTemplate.queryForObject(
                "SELECT texture_type FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        return rs.getString("texture_type");
                    }
                }
        );
    }

    @Override
    public String getTableName() {
        return TABLE_NAME;
    }
}