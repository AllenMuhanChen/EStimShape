package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.allen.pga.PreservedComponentData;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

public class CompsToPreserveManager extends StimPropertyManager<PreservedComponentData> {
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
                        "comps_to_preserve VARCHAR(255) NOT NULL, " +
                        "parent_id BIGINT, " +
                        "parent_comps_preserved VARCHAR(255))"
        );
    }

    @Override
    public void writeProperty(Long stimId, PreservedComponentData data) {
        String compsToPreserve = serializeList(data.getCompsToPreserve());
        Long parentId = data.getParentId();
        String parentCompsPreserved = serializeList(data.getParentCompsPreserved());

        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, comps_to_preserve, parent_id, parent_comps_preserved) " +
                        "VALUES (?, ?, ?, ?) " +
                        "ON DUPLICATE KEY UPDATE comps_to_preserve = ?, parent_id = ?, parent_comps_preserved = ?",
                new Object[]{stimId, compsToPreserve, parentId, parentCompsPreserved,
                        compsToPreserve, parentId, parentCompsPreserved}
        );
    }

    @Override
    public PreservedComponentData readProperty(Long stimId) {
        return (PreservedComponentData) jdbcTemplate.queryForObject(
                "SELECT comps_to_preserve, parent_id, parent_comps_preserved FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        List<Integer> compsToPreserve = deserializeList(rs.getString("comps_to_preserve"));
                        Long parentId = rs.getLong("parent_id");
                        if (rs.wasNull()) {
                            parentId = null;
                        }
                        List<Integer> parentCompsPreserved = deserializeList(rs.getString("parent_comps_preserved"));
                        return new PreservedComponentData(compsToPreserve, parentId, parentCompsPreserved);
                    }
                }
        );
    }

    @Override
    public String getTableName() {
        return TABLE_NAME;
    }

    private String serializeList(List<Integer> value) {
        if (value == null || value.isEmpty()) {
            return "";
        }
        return value.stream()
                .map(String::valueOf)
                .collect(Collectors.joining(","));
    }

    private List<Integer> deserializeList(String value) {
        if (value == null || value.trim().isEmpty()) {
            return new ArrayList<>();
        }
        return Arrays.stream(value.split(","))
                .map(String::trim)
                .map(Integer::parseInt)
                .collect(Collectors.toList());
    }
}