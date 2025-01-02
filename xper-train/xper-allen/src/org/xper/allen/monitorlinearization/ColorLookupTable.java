package org.xper.allen.monitorlinearization;

import org.xper.Dependency;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.*;
import java.util.function.BinaryOperator;
import java.util.function.Consumer;
import java.util.function.Function;
import java.util.stream.Collectors;

public class ColorLookupTable {
    private final Map<String, List<ColorEntry>> colorMap = new HashMap<>();

    @Dependency
    private DataSource dataSource;

    public void init() {
        loadAllColors();
    }

    private void loadAllColors() {
        String sql = "SELECT red, green, blue, luminance FROM MonitorLin";
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql);
             ResultSet rs = stmt.executeQuery()) {

            while (rs.next()) {
                ColorEntry entry = new ColorEntry(
                        rs.getInt("red"),
                        rs.getInt("green"),
                        rs.getInt("blue"),
                        rs.getFloat("luminance")
                );

                // Index by color type
                Function<String, List<ColorEntry>> emptyEntry = new Function<String, List<ColorEntry>>() {
                    @Override
                    public List<ColorEntry> apply(String k) {
                        return new ArrayList<>();
                    }
                };
                if (entry.green == 0 && entry.blue == 0) {
                    colorMap.computeIfAbsent("red", emptyEntry).add(entry);
                }
                if (entry.red == 0 && entry.blue == 0) {
                    colorMap.computeIfAbsent("green", emptyEntry).add(entry);
                }
                if (entry.red == 0 && entry.green != 0 && entry.blue != 0) {
                    colorMap.computeIfAbsent("cyan", emptyEntry).add(entry);
                }
                if (entry.red != 0 && entry.green != 0 && entry.blue == 0) {
                    colorMap.computeIfAbsent("yellow", emptyEntry).add(entry);
                }
                if (entry.red == entry.green && entry.green == entry.blue) {
                    colorMap.computeIfAbsent("gray", emptyEntry).add(entry);
                }
            }

            // Sort lists by luminance
            colorMap.values().forEach(new Consumer<List<ColorEntry>>() {
                @Override
                public void accept(List<ColorEntry> list) {
                    list.sort(Comparator.comparing(new Function<ColorEntry, Float>() {
                        @Override
                        public Float apply(ColorEntry e) {
                            return e.luminance;
                        }
                    }));
                }
            });
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    public Map<Object, Float> getClosestColors(float targetLuminance, String colorType, int n) {
        List<ColorEntry> entries = colorMap.get(colorType.toLowerCase());
        if (entries == null) return Collections.emptyMap();

        List<ColorEntry> sortedEntries = new ArrayList<>(entries);
        Collections.sort(sortedEntries, new Comparator<ColorEntry>() {
            @Override
            public int compare(ColorEntry e1, ColorEntry e2) {
                return Float.compare(
                        Math.abs(e1.luminance - targetLuminance),
                        Math.abs(e2.luminance - targetLuminance)
                );
            }
        });

        Map<Object, Float> result = new LinkedHashMap<Object, Float>();
        for (int i = 0; i < Math.min(n, sortedEntries.size()); i++) {
            ColorEntry e = sortedEntries.get(i);
            result.put(getColorObject(e, colorType), e.luminance);
        }
        return result;
    }
    private Object getColorObject(ColorEntry entry, String colorType) {
        switch (colorType.toLowerCase()) {
            case "red":
            case "gray":
                return entry.red;
            case "green":
                return entry.green;
            case "cyan":
                return new Cyan(entry.green, entry.blue);
            case "yellow":
                return new Yellow(entry.red, entry.green);
            default:
                throw new IllegalArgumentException("Unknown color type: " + colorType);
        }
    }
    private static class ColorEntry {
        final int red, green, blue;
        final float luminance;

        ColorEntry(int red, int green, int blue, float luminance) {
            this.red = red;
            this.green = green;
            this.blue = blue;
            this.luminance = luminance;
        }
    }

    public DataSource getDataSource() {
        return dataSource;
    }

    public void setDataSource(DataSource dataSource) {
        this.dataSource = dataSource;
    }
}