package org.xper.allen.monitorlinearization;

import org.xper.Dependency;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.*;

/**
 * This class is responsible for looking up gain values based on the angle and color combination.
 * from the database and saving it locally for faster access
 */
public class GainLookupTable {
    private final Map<String, List<GainEntry>> gainMap = new HashMap<String, List<GainEntry>>();

    @Dependency
    private DataSource dataSource;

    public void init() {
        loadAllGains();
    }

    private void loadAllGains() {
        String sql = "SELECT angle, gain, colors FROM SinGain";
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql);
             ResultSet rs = stmt.executeQuery()) {

            while (rs.next()) {
                GainEntry entry = new GainEntry(
                        rs.getDouble("angle"),
                        rs.getDouble("gain"),
                        rs.getString("colors")
                );

                String colors = entry.colors;
                if (!gainMap.containsKey(colors)) {
                    gainMap.put(colors, new ArrayList<GainEntry>());
                }
                gainMap.get(colors).add(entry);
            }

            for (List<GainEntry> list : gainMap.values()) {
                Collections.sort(list, new Comparator<GainEntry>() {
                    @Override
                    public int compare(GainEntry e1, GainEntry e2) {
                        return Double.compare(e1.angle, e2.angle);
                    }
                });
            }
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    public double getGain(double angle, String colors) {
        double mappedAngle = Math.abs(180 - Math.abs(angle % 360 - 180));
        List<GainEntry> entries = gainMap.get(colors);
        if (entries == null) {
            throw new IllegalArgumentException("Unknown color combination: " + colors);
        }

        GainEntry closest = null;
        GainEntry secondClosest = null;
        double minDiff = Double.MAX_VALUE;
        double secondMinDiff = Double.MAX_VALUE;

        for (GainEntry entry : entries) {
            double diff = Math.abs(entry.angle - mappedAngle);
            if (diff < minDiff) {
                secondMinDiff = minDiff;
                secondClosest = closest;
                minDiff = diff;
                closest = entry;
            } else if (diff < secondMinDiff) {
                secondMinDiff = diff;
                secondClosest = entry;
            }
        }

        if (closest == null) {
            throw new RuntimeException("No gain values found");
        }

        if (secondClosest == null || closest.angle == secondClosest.angle) {
            return closest.gain;
        }

        return minDiff < secondMinDiff ? closest.gain : secondClosest.gain;
    }

    private static class GainEntry {
        final double angle;
        final double gain;
        final String colors;

        GainEntry(double angle, double gain, String colors) {
            this.angle = angle;
            this.gain = gain;
            this.colors = colors;
        }
    }

    public DataSource getDataSource() {
        return dataSource;
    }

    public void setDataSource(DataSource dataSource) {
        this.dataSource = dataSource;
    }
}