package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.allen.drawing.composition.noisy.NoiseCircle;

import javax.vecmath.Point3d;
import java.sql.ResultSet;
import java.sql.SQLException;

/**
 * Reads/writes the shared noise circle (origin + radius, in the shape's scaled object/world frame)
 * for a stimulus.
 *
 * This is the GA -> NAFC contract: the owner shape (a delta, or a variant for variant-only trials)
 * computes the circle once at generation time and stores it here; deltas validate the parent against
 * it, and NAFC reads it back so every member of a trial group inherits one identical circle (see
 * InheritedNoiseCircleMapper). Persisting it - rather than recomputing in NAFC - guarantees the GA's
 * and NAFC's baked noise PNGs use the same circle and makes the pipeline immune to any future
 * randomness in the placement search.
 */
public class NoiseCirclePropertyManager extends StimPropertyManager<NoiseCircle> {
    private static final String TABLE_NAME = "NoiseCircle";

    public NoiseCirclePropertyManager(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);
    }

    @Override
    public void createTableIfNotExists() {
        jdbcTemplate.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE_NAME + " (" +
                        "stim_id BIGINT PRIMARY KEY, " +
                        "origin_x DOUBLE NOT NULL, " +
                        "origin_y DOUBLE NOT NULL, " +
                        "origin_z DOUBLE NOT NULL, " +
                        "radius_mm DOUBLE NOT NULL)"
        );
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
    public void writeProperty(Long stimId, NoiseCircle circle) {
        Point3d o = circle.getOrigin();
        double r = circle.getRadiusMm();
        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, origin_x, origin_y, origin_z, radius_mm) " +
                        "VALUES (?, ?, ?, ?, ?) " +
                        "ON DUPLICATE KEY UPDATE origin_x=?, origin_y=?, origin_z=?, radius_mm=?",
                new Object[]{stimId, o.x, o.y, o.z, r, o.x, o.y, o.z, r}
        );
    }

    @Override
    public NoiseCircle readProperty(Long stimId) {
        return (NoiseCircle) jdbcTemplate.queryForObject(
                "SELECT origin_x, origin_y, origin_z, radius_mm FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
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

    @Override
    public String getTableName() {
        return TABLE_NAME;
    }
}
