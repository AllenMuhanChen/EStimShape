package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

public class CompsToPreserveManager extends StimPropertyManager<List<Integer>> {
    private static final String TABLE_NAME = "StimCompsToPreserve";

    public CompsToPreserveManager(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);
    }

    public boolean hasProperty(Long stimId) {
        Integer count = (Integer) jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
                Integer.class
        );
        return count != null && count > 0;
    }

    @Override
    public void createTableIfNotExists() {
        jdbcTemplate.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE_NAME + " (" +
                        "stim_id BIGINT PRIMARY KEY, " +
                        "comps_to_preserve VARCHAR(255) NOT NULL)"
        );
    }

    @Override
    public void writeProperty(Long stimId, List<Integer> compsToPreserve) {
        String serialized = serialize(compsToPreserve);
        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, comps_to_preserve) " +
                        "VALUES (?, ?) " +
                        "ON DUPLICATE KEY UPDATE comps_to_preserve = ?",
                new Object[]{stimId, serialized, serialized}
        );
    }

    @Override
    public List<Integer> readProperty(Long stimId) {
        return (List<Integer>) jdbcTemplate.queryForObject(
                "SELECT comps_to_preserve FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        return deserialize(rs.getString("comps_to_preserve"));
                    }
                }
        );
    }

    @Override
    public String getTableName() {
        return TABLE_NAME;
    }

    private String serialize(List<Integer> value) {
        if (value == null || value.isEmpty()) {
            return "";
        }
        return value.stream()
                .map(String::valueOf)
                .collect(Collectors.joining(","));
    }

    private List<Integer> deserialize(String value) {
        if (value == null || value.trim().isEmpty()) {
            return new ArrayList<>();
        }
        return Arrays.stream(value.split(","))
                .map(String::trim)
                .map(Integer::parseInt)
                .collect(Collectors.toList());
    }
}