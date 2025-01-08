package org.xper.allen.drawing.mstickbubbles;

import org.xper.alden.drawing.renderer.AbstractRenderer;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.drawing.Coordinates2D;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.util.*;



public class MStickBubbleGenerator {
    int width = 1000;
    int height = 1000;
    AbstractRenderer renderer;

    public BufferedImage generateBubbleMap(AllenMatchStick matchStick, int numBubbles) throws IOException {
        BufferedImage bubbleMap = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);

        //Aggregate all points on MAXis
        List<Point3d> mAxisPoints = new ArrayList<>();
        Map<Point3d, MAxisPointID> infoForPoints = new HashMap<>();
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

        List<Point3d> sampledPoints = sampleMAxisPoints(numBubbles, correctedMAxisPoints);

        List<Double> radii = findRadiiFor(sampledPoints, matchStick, infoForCorrectedPoints);

        List<Vector3d> perpendicularOffsets = samplePerpendicularOffsets(matchStick, sampledPoints, infoForCorrectedPoints, radii);

        // Draw the perpendicular offsets - for visualization purposes, should not be drawn since it's in the red channel.
        drawPerpOffsets(sampledPoints, perpendicularOffsets, radii, bubbleMap);

        drawSkeleton(correctedMAxisPoints, bubbleMap);

        drawBubbles(sampledPoints, perpendicularOffsets, radii, bubbleMap);

        return bubbleMap;
    }

    /**
     * choose MAxis points to sample for bubbles
     * @param numBubbles
     * @param correctedMAxisPoints
     * @return
     */
    private static List<Point3d> sampleMAxisPoints(int numBubbles, List<Point3d> correctedMAxisPoints) {
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
        return sampledPoints;
    }

    private static List<Double> findRadiiFor(List<Point3d> sampledPoints, AllenMatchStick matchStick, Map<Point3d, MAxisPointID> infoForCorrectedPoints) {
        // Find radius at these sampled points:
        List<Double> radii = new ArrayList<>(sampledPoints.size());
        for (Point3d point : sampledPoints) {
            MAxisPointID id = infoForCorrectedPoints.get(point);
            double radius = matchStick.getComp()[id.compId].getRadiusAcross()[id.uNdx];
            radius *= matchStick.getScaleForMAxisShape();
            radii.add(radius);
        }
        return radii;
    }

    private static List<Vector3d> samplePerpendicularOffsets(AllenMatchStick matchStick, List<Point3d> sampledPoints, Map<Point3d, MAxisPointID> infoForCorrectedPoints, List<Double> radii) {
        // Sample Perpendicular Offset from the MAxis
        List<Vector3d> perpendicularOffsets = new ArrayList<>(sampledPoints.size());
        for (int i = 0; i < sampledPoints.size(); i++) {
            Point3d sampledPoint = sampledPoints.get(i);
            MAxisPointID id = infoForCorrectedPoints.get(sampledPoint);
            double radius = radii.get(i);

            Vector3d directionVector = matchStick.getComp()[id.compId].getmAxisInfo().getmTangent()[id.uNdx];

            // Get perpendicular vector (rotate 90 degrees in 2D)
            // In 2D, if (x,y) is a vector, then (-y,x) is perpendicular to it
            Point3d perpVector = new Point3d(-directionVector.y, directionVector.x, 0);

            perpVector.scale(radius);
            perpendicularOffsets.add(new Vector3d(perpVector));
        }
        return perpendicularOffsets;
    }

    /**
     * Draw bubbles around the sampled points on the medial axis. Sampled points are offset by random amounts
     * perpendicular to their orientations. Radii of bubbles are based on the radii of the shape at
     * the sampled points.
     *
     * @param sampledPoints
     * @param perpendicularOffsets
     * @param radii
     * @param bubbleMap
     */
    private void drawBubbles(List<Point3d> sampledPoints, List<Vector3d> perpendicularOffsets, List<Double> radii, BufferedImage bubbleMap) {
        for (int i = 0; i < sampledPoints.size(); i++) {
            Point3d point = sampledPoints.get(i);
            Vector3d perpOffset = perpendicularOffsets.get(i);
            double radius = mmToPixels(renderer, radii.get(i)); // Convert radius from mm to pixels

            // Create offset point by adding the perpendicular offset vector
            Point3d offsetPoint = new Point3d(point);
            offsetPoint.add(perpOffset);

            // Convert to screen coordinates
            Coordinates2D center = mmToPixels(renderer, new Coordinates2D(offsetPoint.x, offsetPoint.y));

            // Draw circle around each point
            for (int dx = -(int) radius; dx <= radius; dx++) {
                for (int dy = -(int) radius; dy <= radius; dy++) {
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
    }

    /**
     * // Draw the skeleton - for visualzation purposes, should not be drawn in scene since it's in the green channel.
     *
     * @param correctedMAxisPoints
     * @param bubbleMap
     */
    private void drawSkeleton(List<Point3d> correctedMAxisPoints, BufferedImage bubbleMap) {
        for (int i = 1; i < correctedMAxisPoints.size(); i++) {
            Point3d point = correctedMAxisPoints.get(i);
            Coordinates2D xy = mmToPixels(renderer, new Coordinates2D(point.x, point.y));

            // Pack ARGB values manually
            int argb = getDebugARGB();

            bubbleMap.setRGB((int) xy.getX(), (int) xy.getY(), argb);
        }
    }

    private void drawPerpOffsets(List<Point3d> sampledPoints, List<Vector3d> perpendicularOffsets, List<Double> radii, BufferedImage bubbleMap) {
        for (int i = 0; i < sampledPoints.size(); i++) {
            Point3d point = sampledPoints.get(i);
            Vector3d perpOffset = perpendicularOffsets.get(i);
            double radius = mmToPixels(renderer, radii.get(i)); // Convert radius from mm to pixels
            Coordinates2D center = mmToPixels(renderer, new Coordinates2D(point.x, point.y));

            // Calculate start and end points using the perpendicular vector
            Point3d perpendicularStart = new Point3d(point);
            perpendicularStart.add(perpOffset);  // Add the offset vector
            Point3d perpendicularEnd = new Point3d(point);
            perpendicularEnd.sub(perpOffset);    // Subtract the offset vector

            // Convert to screen coordinates
            Coordinates2D start = mmToPixels(renderer, new Coordinates2D(perpendicularStart.x, perpendicularStart.y));
            Coordinates2D end = mmToPixels(renderer, new Coordinates2D(perpendicularEnd.x, perpendicularEnd.y));

            // Draw the line
            int numPoints = 100;
            for (int j = 0; j < numPoints; j++) {
                double t = (double) j / (numPoints - 1);
                double x = start.getX() + t * (end.getX() - start.getX());
                double y = start.getY() + t * (end.getY() - start.getY());

                // Check if the point is within image bounds
                if (x >= 0 && x < width && y >= 0 && y < height) {
                    bubbleMap.setRGB((int) x, (int) y, getDebugARGB());
                }
            }
        }
    }

    private static int getMapARGB() {
        int argb = (255 << 24) |    // Alpha = 255 (fully opaque)
                (255 << 16) |    // Red = 255
                (0 << 8) |    // Green = 0
                0;              // Blue = 0
        return argb;
    }

    private static int getDebugARGB() {
        int argb = (255 << 24) |    // Alpha = 255 (fully opaque)
                (0 << 16) |    // Red = 255
                (255 << 8) |    // Green = 0
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