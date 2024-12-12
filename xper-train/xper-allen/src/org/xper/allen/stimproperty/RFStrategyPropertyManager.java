package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.allen.pga.RFStrategy;
import java.sql.ResultSet;
import java.sql.SQLException;

public class RFStrategyPropertyManager extends StimPropertyManager<RFStrategy> {
    private static final String TABLE_NAME = "StimRFStrategy";

    public RFStrategyPropertyManager(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);
    }

    @Override
    public void createTableIfNotExists() {
        jdbcTemplate.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE_NAME + " (" +
                        "stim_id BIGINT PRIMARY KEY, " +
                        "rf_strategy VARCHAR(50) NOT NULL)"
        );
    }

    @Override
    public void writeProperty(Long stimId, RFStrategy strategy) {
        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, rf_strategy) " +
                        "VALUES (?, ?) " +
                        "ON DUPLICATE KEY UPDATE rf_strategy = ?",
                new Object[]{stimId, strategy.name(), strategy.name()}
        );
    }

    @Override
    public RFStrategy readProperty(Long stimId) {
        return (RFStrategy) jdbcTemplate.queryForObject(
                "SELECT rf_strategy FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        return RFStrategy.valueOf(rs.getString("rf_strategy"));
                    }
                }
        );
    }

    @Override
    public String getTableName() {
        return TABLE_NAME;
    }
}