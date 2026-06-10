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
     * Resolve which table holds the data. Prefer the table that actually has rows (new over old),
     * then the table that merely exists (new over old), defaulting to the new table. This avoids
     * reading from an empty old table that exists only because the DB was templated from an older
     * experiment - which previously split reads (old, empty) from writes (new, populated) and made
     * every read come back empty - while still reading a genuinely un-migrated old table that
     * holds real data.
     */
    private String resolveTableName() {
        if (resolvedTableName != null) {
            return resolvedTableName;
        }
        boolean newExists = tableExists(TABLE_NAME);
        boolean oldExists = tableExists(OLD_TABLE_NAME);
        if (newExists && hasRows(TABLE_NAME)) {
            resolvedTableName = TABLE_NAME;
        } else if (oldExists && hasRows(OLD_TABLE_NAME)) {
            resolvedTableName = OLD_TABLE_NAME;
        } else if (newExists) {
            resolvedTableName = TABLE_NAME;
        } else if (oldExists) {
            resolvedTableName = OLD_TABLE_NAME;
        } else {
            return TABLE_NAME; // neither exists yet; created lazily, don't memoize
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

    private boolean hasRows(String name) {
        Integer count = (Integer) jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM " + name, Integer.class);
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

    /**
     * The stim's hypothesized comp list, or null when the row is missing OR the stored list is
     * empty. Use this instead of readProperty().getHypothesizedComp() wherever a missing row is
     * possible: readProperty throws on a missing row, and rows with an empty comp list exist in
     * the wild (e.g. pre-populated rows for deltas that were never generated).
     */
    public List<Integer> readHypothesizedCompOrNull(Long stimId) {
        if (!hasProperty(stimId)) {
            return null;
        }
        List<Integer> comps = readProperty(stimId).getHypothesizedComp();
        return (comps == null || comps.isEmpty()) ? null : comps;
    }

    @Override
    public void createTableIfNotExists() {
        // Always ensure the new table exists. It no longer shadows a genuinely-populated old table,
        // because resolveTableName() prefers whichever table actually has rows.
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
        // Write to the same table/columns that reads resolve to, so reads and writes never split.
        String table = resolveTableName();
        String compCol = hypothesizedCompColumn();
        String parentCompCol = parentHypothesizedCompsColumn();
        String hypothesizedComp = serializeList(data.getHypothesizedComp());
        Long parentId = data.getParentId();
        String parentHypothesizedComps = serializeList(data.getParentHypothesizedComps());

        jdbcTemplate.update(
                "INSERT INTO " + table + " (stim_id, " + compCol + ", parent_id, " + parentCompCol + ") " +
                        "VALUES (?, ?, ?, ?) " +
                        "ON DUPLICATE KEY UPDATE " + compCol + " = ?, parent_id = ?, " + parentCompCol + " = ?",
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
