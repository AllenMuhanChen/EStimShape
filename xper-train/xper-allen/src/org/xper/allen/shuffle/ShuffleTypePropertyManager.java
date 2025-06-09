package org.xper.allen.shuffle;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.stimproperty.StimPropertyManager;

public class ShuffleTypePropertyManager extends StimPropertyManager<ShuffleType> {
    private static final String TABLE_NAME = "StimShuffleType";

    public ShuffleTypePropertyManager(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);
    }

    @Override
    public void createTableIfNotExists() {
        jdbcTemplate.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE_NAME + " (" +
                        "stim_id BIGINT PRIMARY KEY, " +
                        "shuffle_type VARCHAR(50) NOT NULL)"
        );
    }

    @Override
    public void writeProperty(Long stimId, ShuffleType property) {
        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, shuffle_type) " +
                        "VALUES (?, ?) " +
                        "ON DUPLICATE KEY UPDATE shuffle_type = ?",
                new Object[]{stimId, property.toString(), property.toString()}
        );
    }

    @Override
    public ShuffleType readProperty(Long stimId) {
        return (ShuffleType) jdbcTemplate.queryForObject(
                "SELECT shuffle_type FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
                (rs, rowNum) -> ShuffleType.valueOf(rs.getString("shuffle_type"))
        );
    }

    @Override
    public String getTableName() {
        return TABLE_NAME;
    }
}