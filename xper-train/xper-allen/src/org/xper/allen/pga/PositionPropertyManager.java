package org.xper.allen.pga;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.allen.drawing.composition.experiment.PositioningStrategy;
import org.xper.allen.stimproperty.StimPropertyManager;

import javax.vecmath.Point3d;
import java.sql.ResultSet;
import java.sql.SQLException;

public class PositionPropertyManager extends StimPropertyManager<MStickPosition> {
    private static final String TABLE_NAME = "StimPosition";

    public PositionPropertyManager(JdbcTemplate jdbcTemplate) {
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
                        "positioning_strategy VARCHAR(100) NOT NULL, " +
                        "target_comp INT, " +
                        "location VARCHAR(255) NOT NULL)"
        );
    }

    @Override
    public void writeProperty(Long stimId, MStickPosition property) {
        String positioningStrategy = property.getPositioningStrategy().name();
        Integer targetComp = property.getTargetComp();
        String location = serializePoint3d(property.getPosition());

        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, positioning_strategy, target_comp, location) " +
                        "VALUES (?, ?, ?, ?) " +
                        "ON DUPLICATE KEY UPDATE positioning_strategy = ?, target_comp = ?, location = ?",
                new Object[]{stimId, positioningStrategy, targetComp, location,
                        positioningStrategy, targetComp, location}
        );
    }

    @Override
    public MStickPosition readProperty(Long stimId) {
        return (MStickPosition) jdbcTemplate.queryForObject(
                "SELECT positioning_strategy, target_comp, location FROM " + TABLE_NAME + " WHERE stim_id=?",
                new Object[]{stimId},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        PositioningStrategy strategy = PositioningStrategy.valueOf(rs.getString("positioning_strategy"));
                        Integer targetComp = rs.getInt("target_comp");
                        if (rs.wasNull()) {
                            targetComp = null;
                        }
                        Point3d position = deserializePoint3d(rs.getString("location"));

                        if (targetComp != null) {
                            return new MStickPosition(strategy, targetComp, position);
                        } else {
                            return new MStickPosition(strategy, position);
                        }
                    }
                }
        );
    }

    @Override
    public String getTableName() {
        return TABLE_NAME;
    }

    private String serializePoint3d(Point3d point) {
        if (point == null) {
            return "0.0,0.0,0.0";
        }
        return point.x + "," + point.y + "," + point.z;
    }

    private Point3d deserializePoint3d(String value) {
        if (value == null || value.trim().isEmpty()) {
            return new Point3d(0.0, 0.0, 0.0);
        }
        String[] parts = value.split(",");
        double x = Double.parseDouble(parts[0].trim());
        double y = Double.parseDouble(parts[1].trim());
        double z = Double.parseDouble(parts[2].trim());
        return new Point3d(x, y, z);
    }
}