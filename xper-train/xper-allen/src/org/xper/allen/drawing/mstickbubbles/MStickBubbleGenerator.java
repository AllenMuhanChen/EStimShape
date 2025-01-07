package org.xper.allen.drawing.mstickbubbles;

import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.drawing.Coordinates2D;

import javax.vecmath.Point3d;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.util.*;

public class MStickBubbleGenerator {
    int width = 1000;
    int height = 1000;
    AbstractRenderer renderer;

    public BufferedImage generateBubbleMap(AllenMatchStick matchStick, int numBubbles) throws IOException {

        class MAxisPointID {
            public int compId;
            public int uNdx;

            public MAxisPointID(int compId, int uNdx) {
                this.compId = compId;
                this.uNdx = uNdx;
            }
        }

        //Aggregate all points on MAXis
        Map<Point3d, MAxisPointID> infoForPoints = new HashMap<>();
        BufferedImage bubbleMap = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        List<Point3d> mAxisPoints = new ArrayList<>();
        for (int compId = 1; compId <= matchStick.getNComponent(); compId++) {
            List<Point3d> currentCompsMAxisPoints = Arrays.asList(matchStick.getComp()[compId].getmAxisInfo().getmPts());
//            mAxisPoints.addAll(currentCompsMAxisPoints.subList(1, currentCompsMAxisPoints.size()));
            for (int uNdx = 1; uNdx < currentCompsMAxisPoints.size(); uNdx++) {
                mAxisPoints.add(currentCompsMAxisPoints.get(uNdx));
                infoForPoints.put(currentCompsMAxisPoints.get(uNdx), new MAxisPointID(compId, uNdx));
            }
        }

        // Correct the Medial Axis Points.
        List<Point3d> correctedMAxisPoints = new ArrayList<>(mAxisPoints.size());
        Map<Point3d, MAxisPointID> infoForCorrectedPoints = new HashMap<>();
        Point3d massCenter = matchStick.getMassCenter();
        for (int i = 0; i < mAxisPoints.size(); i++) {
            Point3d originalPoint = mAxisPoints.get(i);
            Point3d correctedPoint = new Point3d(originalPoint);
            correctedPoint.sub(massCenter);
            correctedPoint.scale(matchStick.getScaleForMAxisShape());
            correctedPoint.add(massCenter);
            correctedMAxisPoints.add(i, correctedPoint);
            infoForCorrectedPoints.put(correctedPoint, infoForPoints.get(originalPoint));
        }

        // Sample the axis points
        List<Point3d> sampledPoints = new ArrayList<>();
        if (numBubbles >= correctedMAxisPoints.size()) {
            // If we want more bubbles than points, use all points
            sampledPoints.addAll(correctedMAxisPoints);
        } else {
            // Sample points evenly
            double step = (double) (correctedMAxisPoints.size() - 1) / (numBubbles - 1);
            for (int i = 0; i < numBubbles; i++) {
                int index = (int) Math.round(i * step);
                sampledPoints.add(correctedMAxisPoints.get(Math.min(index, correctedMAxisPoints.size() - 1)));
            }
        }

        // Find radius at these sampled points:
        List<Double> radii = new ArrayList<>(sampledPoints.size());
        for (Point3d point : sampledPoints) {
            MAxisPointID id = infoForCorrectedPoints.get(point);
            double radius = matchStick.getComp()[id.compId].getRadiusAcross()[id.uNdx];
            radius *= matchStick.getScaleForMAxisShape();
            radii.add(radius);
        }


        // Draw the skeleton - for visualzation purposes, should not be drawn since it's in the green channel.
        for (int i = 1; i < correctedMAxisPoints.size(); i++) {
            Point3d point = correctedMAxisPoints.get(i);
            Coordinates2D xy = mmToPixels(renderer, new Coordinates2D(point.x, point.y));

            // Pack ARGB values manually
            int argb = getDebugARGB();

            bubbleMap.setRGB((int) xy.getX(), (int) xy.getY(), argb);
        }

        // Draw the Circle Bubbles
        for (int i = 0; i < sampledPoints.size(); i++) {
            Point3d point = sampledPoints.get(i);
            double radius = mmToPixels(renderer, radii.get(i)); // Convert radius from mm to pixels
            Coordinates2D center = mmToPixels(renderer, new Coordinates2D(point.x, point.y));

            // Draw circle around each point
            for (int dx = -(int)radius; dx <= radius; dx++) {
                for (int dy = -(int)radius; dy <= radius; dy++) {
                    if (dx * dx + dy * dy <= radius * radius) { // Check if point is within circle
                        int x = (int) center.getX() + dx;
                        int y = (int) center.getY() + dy;

                        // Check if the point is within image bounds
                        if (x >= 0 && x < width && y >= 0 && y < height) {
                            bubbleMap.setRGB(x, y, getMapARGB());
                        }
                    }
                }
            }
        }


        return bubbleMap;
    }

    private static int getMapARGB() {
        int argb = (255 << 24) |    // Alpha = 255 (fully opaque)
                (255 << 16) |    // Red = 255
                (0 << 8)    |    // Green = 0
                0;              // Blue = 0
        return argb;
    }

    private static int getDebugARGB() {
        int argb = (255 << 24) |    // Alpha = 255 (fully opaque)
                (0 << 16) |    // Red = 255
                (255 << 8)    |    // Green = 0
                0;              // Blue = 0
        return argb;
    }

    public static Coordinates2D mmToPixels(AbstractRenderer renderer, Coordinates2D mm) {
        return renderer.coord2pixel(mm);
    }
    public static double mmToPixels(AbstractRenderer renderer, double mm) {
        Coordinates2D pixels = renderer.mm2pixel(new Coordinates2D(mm, mm));
        return pixels.getX();

    }
}