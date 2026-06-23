package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.allen.drawing.composition.noisy.NoiseCircle;

import javax.vecmath.Point3d;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * The shared noise circle for a delta trial group, keyed by (parent_id, hypothesized comp-set) - NOT
 * by stim_id like {@link NoiseCirclePropertyManager}.
 *
 * The circle is anchored on the PARENT's hypothesized component (the comp the deltas mutate), so every
 * delta of the same parent that mutates the same comp(s) shares one identical circle. The first such
 * delta computes it from the parent and stores it here; later deltas (and NAFC, which builds a trial
 * group around a variant + its included deltas mutating that comp) read it back and must use it
 * verbatim. Keying on the comp-set (not the individual stim) is what removes noise position/size as a
 * cue across the whole group.
 *
 * The comp-set key is the parent-numbered components, sorted and comma-joined, so {2,1} and {1,2} map
 * to the same row.
 */
public class SharedNoiseCircleManager {
    private static final String TABLE_NAME = "SharedNoiseCircle";
    private final JdbcTemplate jdbcTemplate;

    public SharedNoiseCircleManager(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
        createTableIfNotExists();
    }

    public void createTableIfNotExists() {
        jdbcTemplate.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE_NAME + " (" +
                        "parent_id BIGINT NOT NULL, " +
                        "hypothesized_comps VARCHAR(255) NOT NULL, " +
                        "origin_x DOUBLE NOT NULL, " +
                        "origin_y DOUBLE NOT NULL, " +
                        "origin_z DOUBLE NOT NULL, " +
                        "radius_mm DOUBLE NOT NULL, " +
                        "PRIMARY KEY (parent_id, hypothesized_comps))"
        );
    }

    /** Canonical key for a comp-set: sorted, comma-joined, so order doesn't matter. */
    public static String key(List<Integer> comps) {
        List<Integer> sorted = new ArrayList<>(comps);
        Collections.sort(sorted);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < sorted.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append(sorted.get(i));
        }
        return sb.toString();
    }

    public boolean hasProperty(Long parentId, List<Integer> comps) {
        Integer count = (Integer) jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM " + TABLE_NAME + " WHERE parent_id=? AND hypothesized_comps=?",
                new Object[]{parentId, key(comps)},
                Integer.class
        );
        return count != null && count > 0;
    }

    public void writeProperty(Long parentId, List<Integer> comps, NoiseCircle circle) {
        Point3d o = circle.getOrigin();
        double r = circle.getRadiusMm();
        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (parent_id, hypothesized_comps, origin_x, origin_y, origin_z, radius_mm) " +
                        "VALUES (?, ?, ?, ?, ?, ?) " +
                        "ON DUPLICATE KEY UPDATE origin_x=?, origin_y=?, origin_z=?, radius_mm=?",
                new Object[]{parentId, key(comps), o.x, o.y, o.z, r, o.x, o.y, o.z, r}
        );
    }

    public NoiseCircle readProperty(Long parentId, List<Integer> comps) {
        return (NoiseCircle) jdbcTemplate.queryForObject(
                "SELECT origin_x, origin_y, origin_z, radius_mm FROM " + TABLE_NAME +
                        " WHERE parent_id=? AND hypothesized_comps=?",
                new Object[]{parentId, key(comps)},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        Point3d origin = new Point3d(
                                rs.getDouble("origin_x"),
                                rs.getDouble("origin_y"),
                                rs.getDouble("origin_z"));
                        return new NoiseCircle(origin, rs.getDouble("radius_mm"));
                    }
                }
        );
    }

    public String getTableName() {
        return TABLE_NAME;
    }
}
