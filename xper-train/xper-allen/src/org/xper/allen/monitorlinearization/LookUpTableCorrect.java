package org.xper.allen.monitorlinearization;

import org.xper.Dependency;
import org.xper.drawing.RGBColor;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.BiConsumer;

public class LookUpTableCorrect {

    @Dependency
    DataSource dataSource;
    private double minDiff;
    private int minRed;
    private int minGreen;

    public RGBColor correctRedGreen(double redLuminance, double greenLuminance) {
        double targetLuminance = redLuminance + greenLuminance;
        System.out.println("Target Luminance: " + targetLuminance + " Red Luminance: " + redLuminance + " Green Luminance: " + greenLuminance);
        int n = 5;
        Map<Integer, Float> closestGreens = getClosestColorsWithLuminance((float) greenLuminance, "green", n);
        Map<Integer, Float> closestReds = getClosestColorsWithLuminance((float) redLuminance, "red", n);

        minDiff = Double.MAX_VALUE;
        minRed = 0;
        minGreen = 0;
        closestReds.forEach(new BiConsumer<Integer, Float>() {
            @Override
            public void accept(Integer red, Float redLum) {
                closestGreens.forEach(new BiConsumer<Integer, Float>() {
                    @Override
                    public void accept(Integer green, Float greenLum) {
                        double totalLuminance = redLum + greenLum;
                        double diff = Math.abs(totalLuminance - targetLuminance);
                        if (diff < minDiff) {
                            System.out.println("New Min Found: " + diff + "With Luminance: " + totalLuminance + " Red: " + red + " Green: " + green);                            minDiff = diff;
                            minRed = red;
                            minGreen = green;
                        }
                    }
                });
            }
        });
        System.out.println("Total Corrected Luminance: " + (closestReds.get(minRed) + closestGreens.get(minGreen)));
        System.out.println("Closest Red: " + minRed + " with Luminance " + closestReds.get(minRed));
        System.out.println("Closest Green: " + minGreen + "with Luminance " + closestGreens.get(minGreen));
        return new RGBColor(minRed/255.0f, minGreen/255.0f, 0);

    }

    public Map<Integer, Float> getClosestColorsWithLuminance(float targetLuminance, String colorChannel, int n) {
        Map<Integer, Float> closestColorsWithLuminance = new LinkedHashMap<>();

        String sql = "SELECT " + colorChannel + ", luminance FROM MonitorLin WHERE " + colorChannel + " != 0 ORDER BY ABS(luminance - ?) LIMIT ?";

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {

            stmt.setFloat(1, targetLuminance);
            stmt.setInt(2, n);

            try (ResultSet rs = stmt.executeQuery()) {
                while (rs.next()) {
                    int colorValue = rs.getInt(colorChannel);
                    float luminance = rs.getFloat("luminance");
                    closestColorsWithLuminance.put(colorValue, luminance);
                }
            }
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }

        return closestColorsWithLuminance;
    }

    public DataSource getDataSource() {
        return dataSource;
    }

    public void setDataSource(DataSource dataSource) {
        this.dataSource = dataSource;
    }
}