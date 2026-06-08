package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.allen.pga.HypothesizedCompData;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Reads/writes the hypothesized driving component for a stimulus.
 *
 * The table and columns were renamed from StimCompsToPreserve(comps_to_preserve,
 * parent_comps_preserved) to HypothesizedComp(hypothesized_comp, parent_hypothesized_comps).
 * Reads fall back to the old table/columns so that new code can run against old, un-migrated
 * databases (e.g. NAFC generation against a prior GA experiment's DB) without a migration.
 * Writes and table creation always target the new schema (writes only ever happen on the
 * current experiment's DB, which is freshly created with the new table).
 */
public class HypothesizedCompManager extends StimPropertyManager<HypothesizedCompData> {
    private static final String TABLE_NAME = "HypothesizedComp";
    private static final String OLD_TABLE_NAME = "StimCompsToPreserve";

    private String resolvedTableName;

    public HypothesizedCompManager(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);
    }

    /**
     * Resolve which table holds the data. The old table only exists on old, un-migrated DBs, so
     * its presence is the reliable signal to read from it; otherwise use the new table. (We can't
     * key off the new table's presence because {@link #createTableIfNotExists()} runs in the base
     * constructor and would otherwise auto-create an empty new table even on an old DB.)
     */
    private String resolveTableName() {
        if (resolvedTableName == null) {
            resolvedTableName = tableExists(OLD_TABLE_NAME) ? OLD_TABLE_NAME : TABLE_NAME;
        }
        return resolvedTableName;
    }

    private boolean tableExists(String name) {
        Integer count = (Integer) jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM information_schema.tables " +
                        "WHERE table_schema = DATABASE() AND table_name = ?",
                new Object[]{name},
                Integer.class
        );
        return count != null && count > 0;
    }

    private boolean isOldTable() {
        return OLD_TABLE_NAME.equals(resolveTableName());
    }

    /**
     * True when reading from the old, un-migrated table. Callers that depend on delta rows
     * recording the actually-mutated comp (a Phase-2 behavior) should treat legacy data
     * differently, since old delta rows were written as copies of their parent's row.
     */
    public boolean isLegacyTable() {
        return isOldTable();
    }

    private String hypothesizedCompColumn() {
        return isOldTable() ? "comps_to_preserve" : "hypothesized_comp";
    }

    private String parentHypothesizedCompsColumn() {
        return isOldTable() ? "parent_comps_preserved" : "parent_hypothesized_comps";
    }

    public boolean hasProperty(Long stimId) {
        Integer count = (Integer) jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM " + resolveTableName() + " WHERE stim_id=?",
                new Object[]{stimId},
                Integer.class
        );
        return count != null && count > 0;
    }

    @Override
    public void createTableIfNotExists() {
        // On an un-migrated DB the old table holds the data; don't create an empty new table
        // alongside it (that would shadow the real data in resolveTableName()).
        if (tableExists(OLD_TABLE_NAME)) {
            return;
        }
        jdbcTemplate.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE_NAME + " (" +
                        "stim_id BIGINT PRIMARY KEY, " +
                        "hypothesized_comp VARCHAR(255) NOT NULL, " +
                        "parent_id BIGINT, " +
                        "parent_hypothesized_comps VARCHAR(255))"
        );
    }

    @Override
    public void writeProperty(Long stimId, HypothesizedCompData data) {
        String hypothesizedComp = serializeList(data.getHypothesizedComp());
        Long parentId = data.getParentId();
        String parentHypothesizedComps = serializeList(data.getParentHypothesizedComps());

        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, hypothesized_comp, parent_id, parent_hypothesized_comps) " +
                        "VALUES (?, ?, ?, ?) " +
                        "ON DUPLICATE KEY UPDATE hypothesized_comp = ?, parent_id = ?, parent_hypothesized_comps = ?",
                new Object[]{stimId, hypothesizedComp, parentId, parentHypothesizedComps,
                        hypothesizedComp, parentId, parentHypothesizedComps}
        );
    }

    @Override
    public HypothesizedCompData readProperty(Long stimId) {
        // Alias to the new column names so the mapper is uniform across old/new schemas.
        String sql = "SELECT " + hypothesizedCompColumn() + " AS hypothesized_comp, parent_id, " +
                parentHypothesizedCompsColumn() + " AS parent_hypothesized_comps " +
                "FROM " + resolveTableName() + " WHERE stim_id=?";
        return (HypothesizedCompData) jdbcTemplate.queryForObject(
                sql,
                new Object[]{stimId},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        List<Integer> hypothesizedComp = deserializeList(rs.getString("hypothesized_comp"));
                        Long parentId = rs.getLong("parent_id");
                        if (rs.wasNull()) {
                            parentId = null;
                        }
                        List<Integer> parentHypothesizedComps = deserializeList(rs.getString("parent_hypothesized_comps"));
                        return new HypothesizedCompData(hypothesizedComp, parentId, parentHypothesizedComps);
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
