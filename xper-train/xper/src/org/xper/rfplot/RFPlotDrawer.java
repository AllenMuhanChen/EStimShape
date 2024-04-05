package org.xper.rfplot;

import org.xper.drawing.Coordinates2D;
import org.xper.drawing.GLUtil;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.Square;

import java.util.*;

public class RFPlotDrawer {

    // Additional fields for the enclosing circle
    private Coordinates2D circleCenter;
    private double circleRadius;
    private List<List<Point>> outlines = new LinkedList<>();
    private final List<Coordinates2D> circlePoints = new LinkedList<>();
//    private List<Point> hull;
    private Coordinates2D rfCenter;
//    private Point[] diameterPoints = new Point[2]; // Stores the two points that define the diameter

    public void addCirclePoint(Coordinates2D point){
        circlePoints.add(point);
        System.out.println("Added point: " + point.toString());
        onPointsUpdated();
    }

    public void addOutlinePoints(List<Coordinates2D> outline){
        List<Point> outlinePoints = new ArrayList<>();
        for (Coordinates2D coord: outline){
            outlinePoints.add(new Point(coord.getX(), coord.getY()));
        }
        outlines.add(outlinePoints);
    }

    public void undo(){
        circlePoints.remove(circlePoints.size()-1);
        onPointsUpdated();
    }

    public void removeClosestOutlineTo(Coordinates2D point) {
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
            // Drawing the regular points as yellow circles
            drawCirclePoints();
            drawRFCircle();
            drawRFCenter();

            drawOutlines();
//            // Drawing the hull points as red circles
//            if (hull != null && !hull.isEmpty()) {
//                for (Point hullPoint : hull) {
//                    GLUtil.drawCircle(new Circle(true, 5), hullPoint.x, hullPoint.y, 0, 1, 0, 0); // Red
//                }
//            }




            // Drawing the diameter with a green line, if available
//            if (diameterPoints[0] != null && diameterPoints[1] != null) {
//                GLUtil.drawLine(diameterPoints[0].x, diameterPoints[0].y, diameterPoints[1].x, diameterPoints[1].y, 0, 1, 0); // Green line
//            }


        } catch (Exception e) {
            // It's generally a good practice to at least log exceptions.
            e.printStackTrace();
        }
    }

    private void drawOutlines() {
        for (List<Point> outline: outlines){
            for (int i = 0; i < outline.size(); i++) {
                Point start = outline.get(i);
                Point end = outline.get((i + 1) % outline.size()); // Ensures the last point connects back to the first
                GLUtil.drawLine(start.x, start.y, end.x, end.y, 1, 0, 0); // Red lines
            }
        }
    }

    private void drawRFCircle() {
        if (circleCenter != null && circleRadius > 0) {
            // Assuming GLUtil.drawCircle can take radius as a parameter. Adjust if necessary.
            // Note: The color is set to a different one for distinction, let's say purple (1, 0, 1).
            GLUtil.drawCircle(new Circle(false, circleRadius), // Circle class might need to take diameter, hence radius * 2
                    circleCenter.getX(), circleCenter.getY(), 0,
                    1, 0, 1); // Purple
        }
    }

    private void drawRFCenter() {
        if (rfCenter != null) {
            GLUtil.drawSquare(new Square(true, 10), rfCenter.getX(), rfCenter.getY(), 0, 0, 0, 1); // Blue
        }
    }

    private void drawCirclePoints() {
        for (Coordinates2D point : circlePoints) {
            GLUtil.drawCircle(new Circle(true, 5), point.getX(), point.getY(), 0, 1, 1, 0); // Yellow
        }
    }



    private void onPointsUpdated() {
//        hull = ConvexHull.makeHullFromCoordinates(points);
        computeEnclosingCircle();
        rfCenter = circleCenter;
//        rfCenter = getRFCenter();
//        computeDiameter(); // Update the diameter whenever points are updated
    }

    private void computeEnclosingCircle() {
        if (circlePoints.isEmpty()) {
            circleCenter = null;
            circleRadius = 0;
            return;
        }

        // Compute the center as the average of all points
        double sumX = 0, sumY = 0;
        for (Coordinates2D point : circlePoints) {
            sumX += point.getX();
            sumY += point.getY();
        }
        double centerX = sumX / circlePoints.size();
        double centerY = sumY / circlePoints.size();
        circleCenter = new Coordinates2D(centerX, centerY);

        // Compute the radius as the average distance to the points
        double sumDistance = 0;
        for (Coordinates2D point : circlePoints) {
            sumDistance += point.distance(circleCenter);
        }
        circleRadius = sumDistance / circlePoints.size();

    }

    // New method to compute the diameter
//    private void computeDiameter() {
//        double maxDistanceSquared = 0;
//        for (int i = 0; i < hull.size(); i++) {
//            for (int j = i + 1; j < hull.size(); j++) {
//                double distanceSquared = distanceSquared(hull.get(i), hull.get(j));
//                if (distanceSquared > maxDistanceSquared) {
//                    maxDistanceSquared = distanceSquared;
//                    diameterPoints[0] = hull.get(i);
//                    diameterPoints[1] = hull.get(j);
//                }
//            }
//        }
//    }

    // Helper method to calculate squared distance between two points
    private double distanceSquared(Point p1, Point p2) {
        double dx = p1.x - p2.x;
        double dy = p1.y - p2.y;
        return dx * dx + dy * dy;
    }

    public Coordinates2D getRFCenter(){
        return circleCenter;
    }
//
//    public List<Coordinates2D> getHull(){
//        List<Coordinates2D> hullCoords = pointsToCoords(hull);
//        return hullCoords;
//    }

    private List<Coordinates2D> pointsToCoords(List<Point> hull) {
        List<Coordinates2D> hullCoords = new LinkedList<>();
        for (Point point: hull){
            hullCoords.add(point2Coordinates2D(point));
        }
        return hullCoords;
    }

    private Coordinates2D point2Coordinates2D(Point point) {
        return new Coordinates2D(point.x, point.y);
    }


    public List<Coordinates2D> getCirclePoints(){
        return circlePoints;
    }

    private Point findCentroid(List<Point> points){
        double numPoints = points.size();
        double sumX=0;
        double sumY=0;
        for (Point point:points){
            sumX+=point.x;
            sumY+=point.y;
        }
        Point centroid = new Point(sumX/numPoints, sumY/numPoints);
        return centroid;
    }

    public Coordinates2D getCircleCenter() {
        return circleCenter;
    }

    public double getCircleRadius() {
        return circleRadius;
    }

    public List<Coordinates2D> getOutline() {
        List<Coordinates2D> outlinePoints = new ArrayList<>();
        if (circleCenter == null || circleRadius <= 0) {
            return outlinePoints; // Return an empty list if there's no valid circle.
        }

        // Calculate the points
        double increment = 2 * Math.PI / 100; // 2*PI radians for a full circle, divided into 100 points.
        for (int i = 0; i < 100; i++) {
            double theta = i * increment;
            double x = circleCenter.getX() + circleRadius * Math.cos(theta);
            double y = circleCenter.getY() + circleRadius * Math.sin(theta);
            outlinePoints.add(new Coordinates2D(x, y));
        }

        return outlinePoints;
    }
}