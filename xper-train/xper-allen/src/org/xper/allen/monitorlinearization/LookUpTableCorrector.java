package org.xper.allen.monitorlinearization;

import org.xper.Dependency;
import org.xper.drawing.RGBColor;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.BiConsumer;

public class LookUpTableCorrector {

    @Dependency
    DataSource dataSource;
    private double minDiff;
    private int minRed;
    private int minGreen;

    public RGBColor correctSingleColor(double targetLuminance, String colorchannel) {
        int n = 5;

        Map<Object, Float> closestColors = new LinkedHashMap<>();
        if (colorchannel.equalsIgnoreCase("red") ||
                colorchannel.equalsIgnoreCase(("green"))) {
            Map<Integer, Float> closestRedGreen = getClosestColorsWithLuminance((float) targetLuminance, colorchannel, n);
            closestColors.putAll(closestRedGreen);
        } else if (colorchannel.equalsIgnoreCase("cyan") || colorchannel.equalsIgnoreCase("yellow")) {
            Map<Object, Float> closestDerived = getClosestDerivedColorsWithLuminance((float) targetLuminance, colorchannel, n);
            closestColors.putAll(closestDerived);
        } else {
            throw new IllegalArgumentException("Color channel must be either 'red' or 'green'");
        }


        Object minColor = null;
        float minLuminance = Float.MAX_VALUE;
        for (Map.Entry<Object, Float> entry : closestColors.entrySet()) {
            Object color = entry.getKey();
            float luminance = entry.getValue();
            //look for the cloeset to red Luminance
            if (Math.abs(luminance - targetLuminance) < minLuminance) {
                minColor = color;
                minLuminance = luminance;
            }
        }
        if (minColor == null) {
            throw new RuntimeException("No closest color found");
        }

        if (colorchannel.equals("red")) {
            return new RGBColor((int)minColor/255.0f, 0, 0);
        }
        if (colorchannel.equals("green")) {
            return new RGBColor(0, (int)minColor/255.0f, 0);
        }
        if (colorchannel.equals("yellow")) {
            return new RGBColor(((Yellow)minColor).getRed()/255.0f, ((Yellow)minColor).getGreen()/255.0f, 0);
        }
        if (colorchannel.equals("cyan")) {
            return new RGBColor(0, ((Cyan)minColor).getGreen()/255.0f, ((Cyan)minColor).getBlue()/255.0f);
        }
        else {
            throw new IllegalArgumentException("Color channel must be either 'red', 'green', 'cyan', or 'yellow'");
        }

    }

    public RGBColor correctRedGreen(double redLuminance, double greenLuminance) {
        double targetLuminance = redLuminance + greenLuminance;
        int n = 5;
        Map<Integer, Float> closestGreens = getClosestColorsWithLuminance((float) greenLuminance, "green", n);
        Map<Integer, Float> closestReds = getClosestColorsWithLuminance((float) redLuminance, "red", n);
//        closestGreens.put(0, 0.0f);
//        closestReds.put(0, 0.0f);

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
                            minRed = red;
                            minGreen = green;
                        }
                    }
                });
            }
        });
        return new RGBColor(minRed/255.0f, minGreen/255.0f, 0);

    }

    public RGBColor correctCyanYellow(double targetCyanLuminance, double targetYellowLuminance) {
        double targetSumLuminance = targetCyanLuminance + targetYellowLuminance;
        int n = 5; // Number of closest matches for each color

        // Fetch closest Cyan and Yellow pairs
        Map<Object, Float> closestCyans = getClosestDerivedColorsWithLuminance((float) targetCyanLuminance, "Cyan", n);
        Map<Object, Float> closestYellows = getClosestDerivedColorsWithLuminance((float) targetYellowLuminance, "Yellow", n);
        closestCyans.put(new Cyan(0, 0), 0.0f);
        closestYellows.put(new Yellow(0, 0), 0.0f);

        double minDiff = Double.MAX_VALUE;
        Cyan bestCyan = null;
        Yellow bestYellow = null;

        // Iterate to find the best Cyan and Yellow combination
        for (Map.Entry<Object, Float> cyanEntry : closestCyans.entrySet()) {
            for (Map.Entry<Object, Float> yellowEntry : closestYellows.entrySet()) {
                Cyan cyan = (Cyan) cyanEntry.getKey();
                Yellow yellow = (Yellow) yellowEntry.getKey();
                float cyanLuminance = cyanEntry.getValue();
                float yellowLuminance = yellowEntry.getValue();

                double totalLuminance = cyanLuminance + yellowLuminance;
                double diff = Math.abs(totalLuminance - targetSumLuminance);

                if (diff < minDiff) {
                    minDiff = diff;
                    bestCyan = cyan;
                    bestYellow = yellow;
                }
            }
        }



        if (bestCyan != null && bestYellow != null) {
            // For Cyan: use Green and Blue components. Yellow uses Red and Green, Blue is 0 for Yellow.
            float red = bestYellow.getRed() / 255.0f;
            float green = (Math.max(bestCyan.getGreen(), bestYellow.getGreen()) / 255.0f); // Average Green from both
            float blue = bestCyan.getBlue() / 255.0f;

            return new RGBColor(red, green, blue);
        } else {
            throw new RuntimeException("No best Cyan and Yellow combination found");
        }
    }

    public Map<Integer, Float> getClosestColorsWithLuminance(float targetLuminance, String colorChannel, int n) {
        Map<Integer, Float> closestColorsWithLuminance = new LinkedHashMap<>();

        // Build the SQL query to select only rows where the specified color channel is non-zero
        // and the other color channels are zero.
        String sqlTemplate = "SELECT %s, luminance FROM MonitorLin WHERE %s != 0 AND %s = 0 AND %s = 0 ORDER BY ABS(luminance - ?) LIMIT ?";
        String otherChannel1 = "red";
        String otherChannel2 = "green";
        if ("red".equalsIgnoreCase(colorChannel)) {
            otherChannel1 = "green";
            otherChannel2 = "blue";
        } else if ("green".equalsIgnoreCase(colorChannel)) {
            otherChannel1 = "red";
            otherChannel2 = "blue";
        } else if ("blue".equalsIgnoreCase(colorChannel)) {
            otherChannel1 = "red";
            otherChannel2 = "green";
        }

        String sql = String.format(sqlTemplate, colorChannel, colorChannel, otherChannel1, otherChannel2);

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


    public Map<Object, Float> getClosestDerivedColorsWithLuminance(float targetLuminance, String derivedColor, int n) {
        Map<Object, Float> closestColorsWithLuminance = new LinkedHashMap<>();

        // SQL query setup
        String sql = "";
        if ("Cyan".equalsIgnoreCase(derivedColor)) {
            sql = "SELECT green, blue, luminance FROM MonitorLin WHERE red = 0 AND green != 0 AND blue != 0 ORDER BY ABS(luminance - ?) LIMIT ?";
        } else if ("Yellow".equalsIgnoreCase(derivedColor)) {
            sql = "SELECT red, green, luminance FROM MonitorLin WHERE red != 0 AND green != 0 AND blue = 0 ORDER BY ABS(luminance - ?) LIMIT ?";
        } else {
            throw new IllegalArgumentException("Derived color must be either 'Cyan' or 'Yellow'");
        }

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {

            stmt.setFloat(1, targetLuminance);
            stmt.setInt(2, n);

            try (ResultSet rs = stmt.executeQuery()) {
                while (rs.next()) {
                    if ("Cyan".equalsIgnoreCase(derivedColor)) {
                        int green = rs.getInt("green");
                        int blue = rs.getInt("blue");
                        Cyan cyan = new Cyan(green, blue);
                        closestColorsWithLuminance.put(cyan, rs.getFloat("luminance"));
                    } else {
                        int red = rs.getInt("red");
                        int green = rs.getInt("green");
                        Yellow yellow = new Yellow(red, green);
                        closestColorsWithLuminance.put(yellow, rs.getFloat("luminance"));
                    }
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