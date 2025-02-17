package org.xper.allen.monitorlinearization;

import org.xper.Dependency;
import org.xper.drawing.RGBColor;

import java.util.Map;

public class LookUpTableCorrector {

    @Dependency
    private ColorLookupTable lookupTable;

    public RGBColor correctSingleColor(double targetLuminance, String colorChannel) {
        int n = 5;
        Map<Object, Float> closestColors = lookupTable.getClosestColors((float)targetLuminance, colorChannel, n);

        Object minColor = null;
        float minLuminance = Float.MAX_VALUE;
        for (Map.Entry<Object, Float> entry : closestColors.entrySet()) {
            if (Math.abs(entry.getValue() - targetLuminance) < Math.abs(minLuminance - targetLuminance)) {
                minColor = entry.getKey();
                minLuminance = entry.getValue();
            }
        }

        if (minColor == null) {
            throw new RuntimeException("No closest color found: " + targetLuminance + " " + colorChannel);
        }

        switch(colorChannel.toLowerCase()) {
            case "red":
                return new RGBColor((int)minColor/255.0f, 0, 0);
            case "green":
                return new RGBColor(0, (int)minColor/255.0f, 0);
            case "yellow":
                Yellow y = (Yellow)minColor;
                return new RGBColor(y.getRed()/255.0f, y.getGreen()/255.0f, 0);
            case "orange":
                Orange o = (Orange)minColor;
                return new RGBColor(o.getRed()/255.0f, o.getGreen()/255.0f, 0);
            case "cyan":
                Cyan c = (Cyan)minColor;
                return new RGBColor(0, c.getGreen()/255.0f, c.getBlue()/255.0f);
            case "gray":
                return new RGBColor((int)minColor/255.0f, (int)minColor/255.0f, (int)minColor/255.0f);
            default:
                throw new IllegalArgumentException("Invalid color channel: " + colorChannel);
        }
    }

    public RGBColor correctRedGreen(double redLuminance, double greenLuminance) {
        Map<Object, Float> redColors = lookupTable.getClosestColors((float)redLuminance, "red", 5);
        Map<Object, Float> greenColors = lookupTable.getClosestColors((float)greenLuminance, "green", 5);

        double minDiff = Double.MAX_VALUE;
        int bestRed = 0, bestGreen = 0;
        double targetLuminance = redLuminance + greenLuminance;

        for (Map.Entry<Object, Float> redEntry : redColors.entrySet()) {
            for (Map.Entry<Object, Float> greenEntry : greenColors.entrySet()) {
                double totalLuminance = redEntry.getValue() + greenEntry.getValue();
                double diff = Math.abs(totalLuminance - targetLuminance);
                if (diff < minDiff) {
                    minDiff = diff;
                    bestRed = (int)redEntry.getKey();
                    bestGreen = (int)greenEntry.getKey();
                }
            }
        }

        return new RGBColor(bestRed/255.0f, bestGreen/255.0f, 0);
    }
    public RGBColor correctCyanOrange(double targetCyanLuminance, double targetOrangeLuminance){
        Map<Object, Float> cyanColors = lookupTable.getClosestColors((float)targetCyanLuminance, "cyan", 5);
        Map<Object, Float> orangeColors = lookupTable.getClosestColors((float)targetOrangeLuminance, "orange", 5);

        double minDiff = Double.MAX_VALUE;
        Cyan bestCyan = null;
        Orange bestOrange = null;
        double targetSumLuminance = targetCyanLuminance + targetOrangeLuminance;

        for (Map.Entry<Object, Float> cyanEntry : cyanColors.entrySet()) {
            for (Map.Entry<Object, Float> orangeEntry : orangeColors.entrySet()) {
                double totalLuminance = cyanEntry.getValue() + orangeEntry.getValue();
                double diff = Math.abs(totalLuminance - targetSumLuminance);
                if (diff < minDiff) {
                    minDiff = diff;
                    bestCyan = (Cyan)cyanEntry.getKey();
                    bestOrange = (Orange)orangeEntry.getKey();
                }
            }
        }

        if (bestCyan == null || bestOrange == null) {
            throw new RuntimeException("No best combination found");
        }

        return new RGBColor(
                bestOrange.getRed() / 255.0f,
//                Math.max(bestCyan.getGreen(), bestOrange.getGreen()) / 255.0f,
                Math.min((bestCyan.getGreen() + bestOrange.getGreen()) / 255.0f, 1.0f),
                bestCyan.getBlue() / 255.0f
        );
    }
    public RGBColor correctCyanYellow(double targetCyanLuminance, double targetYellowLuminance) {
        Map<Object, Float> cyanColors = lookupTable.getClosestColors((float)targetCyanLuminance, "cyan", 5);
        Map<Object, Float> yellowColors = lookupTable.getClosestColors((float)targetYellowLuminance, "yellow", 5);

        double minDiff = Double.MAX_VALUE;
        Cyan bestCyan = null;
        Yellow bestYellow = null;
        double targetSumLuminance = targetCyanLuminance + targetYellowLuminance;

        for (Map.Entry<Object, Float> cyanEntry : cyanColors.entrySet()) {
            for (Map.Entry<Object, Float> yellowEntry : yellowColors.entrySet()) {
                double totalLuminance = cyanEntry.getValue() + yellowEntry.getValue();
                double diff = Math.abs(totalLuminance - targetSumLuminance);
                if (diff < minDiff) {
                    minDiff = diff;
                    bestCyan = (Cyan)cyanEntry.getKey();
                    bestYellow = (Yellow)yellowEntry.getKey();
                }
            }
        }

        if (bestCyan == null || bestYellow == null) {
            throw new RuntimeException("No best combination found");
        }

        return new RGBColor(
                bestYellow.getRed() / 255.0f,
                Math.max(bestCyan.getGreen(), bestYellow.getGreen()) / 255.0f,
                bestCyan.getBlue() / 255.0f
        );
    }

    public void setLookupTable(ColorLookupTable lookupTable) {
        this.lookupTable = lookupTable;
    }
}