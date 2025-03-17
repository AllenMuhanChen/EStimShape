package org.xper.rfplot;

import org.xper.drawing.Coordinates2D;
import org.xper.drawing.GLUtil;
import org.xper.drawing.RGBColor;
import org.xper.drawing.object.Square;
import java.util.*;

/**
 * Whole class works in mm. Convert from deg to mm before using.

 */
public class RFPlotDrawer {

    //main data
    Map<String, CircleRF> rfsForChannels =  new LinkedHashMap<String, CircleRF>();
    Map<String, List<List<Point>>> outlinesForChannels = new LinkedHashMap<>();
    Map<String, RGBColor> colorsForChannels = new LinkedHashMap<>();


    private final List<RGBColor> visibleColors = Arrays.asList(
            new RGBColor(1, 0, 0), // Red
            new RGBColor(0, 1, 0), // Lime
            new RGBColor(0, 0, 1), // Blue
            new RGBColor(0, 1, 1), // Cyan
            new RGBColor(1, 0, 1), // Magenta
            new RGBColor(1, 0.5f, 0), // Orange
            new RGBColor(0.5f, 1, 0), // Lime
            new RGBColor(1f, 0, 0.5f), // Purple
            new RGBColor(0.5f, 0, 1), // Purple
            new RGBColor(0, 0.5f, 1),
            new RGBColor(0, 1, 0.5f)
    );

    //private helper variables
    private String currentChannel;
    private Coordinates2D rfCenter;
    private float r;
    private float g;
    private float b;
    private int lastColorIndex = -1;
    private RGBColor color;

    public void changeChannel(String channel){
        currentChannel = channel;

        rfsForChannels.putIfAbsent(channel, new CircleRF());
        outlinesForChannels.putIfAbsent(channel, new LinkedList<>());
        colorsForChannels.putIfAbsent(channel, getNextColor());
    }

    public void removeChannel(String channel){
        rfsForChannels.remove(channel);
        outlinesForChannels.remove(channel);
        colorsForChannels.remove(channel);
    }

    private RGBColor getNextColor() {
        lastColorIndex = (lastColorIndex + 1) % visibleColors.size();
        return visibleColors.get(lastColorIndex);
    }

    public void addCirclePoint(Coordinates2D point){
        if (currentChannel == null){
            System.err.println("No channel selected. Please select a channel type and number");
        }
        rfsForChannels.get(currentChannel).addCirclePoint(point);
        System.out.println("Added point: " + point.toString());
        onPointsUpdated();
    }

    public void addOutlinePoints(List<Coordinates2D> outline){
        List<List<Point>> outlines = outlinesForChannels.get(currentChannel);
        List<Point> outlinePoints = new ArrayList<>();
        for (Coordinates2D coord: outline){
            outlinePoints.add(new Point(coord.getX(), coord.getY()));
        }
        outlines.add(outlinePoints);
    }


    public void removeClosestOutlineTo(Coordinates2D point) {
        List<List<Point>> outlines = outlinesForChannels.get(currentChannel);
        if (outlines.isEmpty()) {
            return; // Early return if there are no outlines to remove.
        }

        // Initialize variables to track the closest outline and its minimum distance to the point.
        double minDistance = Double.MAX_VALUE;
        List<Point> closestOutline = null;

        for (List<Point> outline : outlines) {
            for (Point outlinePoint : outline) {
                double distance = Math.sqrt(Math.pow(outlinePoint.x - point.getX(), 2) + Math.pow(outlinePoint.y - point.getY(), 2));
                if (distance < minDistance) {
                    minDistance = distance;
                    closestOutline = outline;
                }
            }
        }

        // Remove the closest outline from the list if it's found.
        if (closestOutline != null) {
            outlines.remove(closestOutline);
        }
    }


    public void removeClosestCirclePointTo(Coordinates2D point){
        List<Coordinates2D> circlePoints = rfsForChannels.get(currentChannel).getCirclePoints();
        Coordinates2D nearest = Collections.min(circlePoints, new Comparator<Coordinates2D>(){
            @Override
            public int compare(Coordinates2D o1, Coordinates2D o2) {
                return (int) (o1.distance(point) - o2.distance(point));
            }
        });
        circlePoints.remove(nearest);
        onPointsUpdated();
    }
    public void draw() {
        try {
            for (String channel: rfsForChannels.keySet()){
                color = colorsForChannels.get(channel);
                assignCurrentColor(channel);
                drawCirclePoints(color, channel);
                drawRFCircle(color, channel);
                drawRFCenter(color, channel);
                drawOutlines(color, channel);
            }


        } catch (Exception e) {
            // It's generally a good practice to at least log exceptions.
            e.printStackTrace();
        }
    }

    private void assignCurrentColor(String channel) {
        // Default to white if not found
        color = colorsForChannels.getOrDefault(channel, new RGBColor(255, 255, 255));
    }

    private void drawOutlines(RGBColor color, String channel) {
        List<List<Point>> outlines = outlinesForChannels.get(channel);
        for (List<Point> outline: outlines){
            for (int i = 0; i < outline.size(); i++) {
                Point start = outline.get(i);
                Point end = outline.get((i + 1) % outline.size()); // Ensures the last point connects back to the first
                GLUtil.drawLine(start.x, start.y, end.x, end.y, color.getRed(), color.getGreen(), color.getBlue());
            }
        }
    }

    private void drawRFCircle(RGBColor color, String channel) {
        Coordinates2D circleCenter = rfsForChannels.get(channel).getCircleCenter();
        double circleRadius = rfsForChannels.get(channel).getCircleRadius();
        if (circleCenter != null && circleRadius > 0) {
            // Assuming GLUtil.drawCircle can take radius as a parameter. Adjust if necessary.
            // Note: The color is set to a different one for distinction, let's say purple (1, 0, 1).
            GLUtil.drawCircle(new org.xper.drawing.object.Circle(false, circleRadius), // Circle class might need to take diameter, hence radius * 2
                    circleCenter.getX(), circleCenter.getY(), 0,
                    color.getRed(), color.getGreen(), color.getBlue()); // Purple
        }
    }

    private void drawRFCenter(RGBColor color, String channel) {
        rfCenter = rfsForChannels.get(channel).getCircleCenter();
        if (rfCenter != null) {
            GLUtil.drawSquare(new Square(true, 10), rfCenter.getX(), rfCenter.getY(), 0, color.getRed(), color.getGreen(), color.getBlue()); // Blue
        }
    }

    private void drawCirclePoints(RGBColor color, String channel) {
        List<Coordinates2D> circlePoints = rfsForChannels.get(channel).getCirclePoints();
        for (Coordinates2D point : circlePoints) {
            GLUtil.drawCircle(new org.xper.drawing.object.Circle(true, 5), point.getX(), point.getY(), 0, color.getRed(), color.getGreen(), color.getBlue()); // Yellow
        }
    }



    private void onPointsUpdated() {
//        hull = ConvexHull.makeHullFromCoordinates(points);
        computeEnclosingCircle();
        rfCenter = rfsForChannels.get(currentChannel).getCircleCenter();
//        rfCenter = getRFCenter();
//        computeDiameter(); // Update the diameter whenever points are updated
    }

    /**
     * Welzl's randomized algorithm to find the minimum enclosing circle.
     */
    private void computeEnclosingCircle() {
        List<Coordinates2D> circlePoints = rfsForChannels.get(currentChannel).getCirclePoints();
        if (circlePoints.isEmpty()) {
            rfsForChannels.get(currentChannel).setCircleCenter(null);
            rfsForChannels.get(currentChannel).setCircleRadius(0);
            return;
        }

        // Convert to array for easier manipulation
        Coordinates2D[] points = circlePoints.toArray(new Coordinates2D[0]);

        // Find the minimum enclosing circle
        MinCircle result = findMinCircle(points, points.length);

        // Set the results
        rfsForChannels.get(currentChannel).setCircleCenter(result.center);
        rfsForChannels.get(currentChannel).setCircleRadius(result.radius);
    }

    // MinCircle class to hold the circle information
    private static class MinCircle {
        Coordinates2D center;
        double radius;

        MinCircle(Coordinates2D center, double radius) {
            this.center = center;
            this.radius = radius;
        }
    }

    // Returns the minimum enclosing circle for a set of points
    private MinCircle findMinCircle(Coordinates2D[] points, int n) {
        // Base cases
        if (n == 0) {
            return new MinCircle(new Coordinates2D(0, 0), 0);
        }
        if (n == 1) {
            return new MinCircle(points[0], 0);
        }

        // Shuffle the array to improve expected runtime
        randomShuffle(points, n);

        // Initialize circle with first point
        MinCircle circle = new MinCircle(points[0], 0);

        // Add points one by one
        for (int i = 1; i < n; i++) {
            // If the point is outside the current circle
            if (!isInside(circle, points[i])) {
                // Create a new circle with this point on the boundary
                circle = new MinCircle(points[i], 0);

                // Include all previous points in this circle
                for (int j = 0; j < i; j++) {
                    if (!isInside(circle, points[j])) {
                        // Create a circle with both points
                        circle = circleFrom2Points(points[i], points[j]);

                        // Include all previous points in this circle
                        for (int k = 0; k < j; k++) {
                            if (!isInside(circle, points[k])) {
                                // Circle through three points
                                circle = circleFrom3Points(points[i], points[j], points[k]);
                            }
                        }
                    }
                }
            }
        }

        return circle;
    }

    // Checks if a point is inside a circle
    private boolean isInside(MinCircle circle, Coordinates2D point) {
        if (circle.center == null) return false;

        double dx = point.getX() - circle.center.getX();
        double dy = point.getY() - circle.center.getY();
        double distance = Math.sqrt(dx*dx + dy*dy);

        return distance <= circle.radius + 1e-10; // Small epsilon for floating point errors
    }

    // Returns the circle defined by two points (as diameter)
    private MinCircle circleFrom2Points(Coordinates2D p1, Coordinates2D p2) {
        double centerX = (p1.getX() + p2.getX()) / 2.0;
        double centerY = (p1.getY() + p2.getY()) / 2.0;
        Coordinates2D center = new Coordinates2D(centerX, centerY);

        double dx = p2.getX() - p1.getX();
        double dy = p2.getY() - p1.getY();
        double radius = Math.sqrt(dx*dx + dy*dy) / 2.0;

        return new MinCircle(center, radius);
    }

    // Returns the circle defined by three points
    private MinCircle circleFrom3Points(Coordinates2D p1, Coordinates2D p2, Coordinates2D p3) {
        // Using the circumcenter formula for a triangle

        // First, we calculate the perpendicular bisector of two sides
        double x1 = p1.getX();
        double y1 = p1.getY();
        double x2 = p2.getX();
        double y2 = p2.getY();
        double x3 = p3.getX();
        double y3 = p3.getY();

        double a = x1 * (y2 - y3) - y1 * (x2 - x3) + x2 * y3 - x3 * y2;

        // Check if the points are collinear (or nearly so)
        if (Math.abs(a) < 1e-10) {
            // If collinear, find the two furthest points and use them
            double d12 = (x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2);
            double d13 = (x1 - x3) * (x1 - x3) + (y1 - y3) * (y1 - y3);
            double d23 = (x2 - x3) * (x2 - x3) + (y2 - y3) * (y2 - y3);

            if (d12 >= d13 && d12 >= d23) {
                return circleFrom2Points(p1, p2);
            } else if (d13 >= d12 && d13 >= d23) {
                return circleFrom2Points(p1, p3);
            } else {
                return circleFrom2Points(p2, p3);
            }
        }

        // Calculate the circles parameters
        double b = ((x1*x1 + y1*y1) * (y2 - y3) +
                (x2*x2 + y2*y2) * (y3 - y1) +
                (x3*x3 + y3*y3) * (y1 - y2)) / (2 * a);

        double c = ((x1*x1 + y1*y1) * (x3 - x2) +
                (x2*x2 + y2*y2) * (x1 - x3) +
                (x3*x3 + y3*y3) * (x2 - x1)) / (2 * a);

        double centerX = b;
        double centerY = c;
        Coordinates2D center = new Coordinates2D(centerX, centerY);

        // Calculate radius as distance from center to any point
        double dx = centerX - x1;
        double dy = centerY - y1;
        double radius = Math.sqrt(dx*dx + dy*dy);

        return new MinCircle(center, radius);
    }

    // Random shuffle to improve performance
    private void randomShuffle(Coordinates2D[] points, int n) {
        Random rand = new Random();
        for (int i = n - 1; i > 0; i--) {
            int j = rand.nextInt(i + 1);
            // Swap points[i] and points[j]
            Coordinates2D temp = points[i];
            points[i] = points[j];
            points[j] = temp;
        }
    }

    public Coordinates2D getRFCenter(){
        return rfsForChannels.get(currentChannel).getCircleCenter();
    }

    public double getRFDiameter(){
        return rfsForChannels.get(currentChannel).getCircleRadius() * 2;
    }

    public Map<String, RGBColor> getColorsForChannels() {
        return colorsForChannels;
    }

    public Map<String, CircleRF> getRfsForChannels() {
        return rfsForChannels;
    }
}