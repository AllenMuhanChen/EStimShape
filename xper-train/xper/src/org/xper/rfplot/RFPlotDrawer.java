package org.xper.rfplot;

import org.xper.drawing.Coordinates2D;
import org.xper.drawing.GLUtil;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.Square;

import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedList;
import java.util.List;

public class RFPlotDrawer {

    // Additional fields for the enclosing circle
    private Coordinates2D circleCenter;
    private double circleRadius;

    private final List<Coordinates2D> points = new LinkedList<>();
//    private List<Point> hull;
    private Coordinates2D rfCenter;
//    private Point[] diameterPoints = new Point[2]; // Stores the two points that define the diameter

    public void draw() {
        try {
            // Drawing the regular points as yellow circles
            for (Coordinates2D point : points) {
                GLUtil.drawCircle(new Circle(true, 5), point.getX(), point.getY(), 0, 1, 1, 0); // Yellow
            }

//            // Drawing the hull points as red circles
//            if (hull != null && !hull.isEmpty()) {
//                for (Point hullPoint : hull) {
//                    GLUtil.drawCircle(new Circle(true, 5), hullPoint.x, hullPoint.y, 0, 1, 0, 0); // Red
//                }
//            }

            // Drawing the hull as a polygon
//            if (hull != null && !hull.isEmpty()) {
//                int hullSize = hull.size();
//                for (int i = 0; i < hullSize; i++) {
//                    Point start = hull.get(i);
//                    Point end = hull.get((i + 1) % hullSize); // Ensures the last point connects back to the first
//                    GLUtil.drawLine(start.x, start.y, end.x, end.y, 1, 0, 0); // Red lines
//                }
//            }

            // Drawing the RF center as a blue square
            if (rfCenter != null) {
                GLUtil.drawSquare(new Square(true, 10), rfCenter.getX(), rfCenter.getY(), 0, 0, 0, 1); // Blue
            }

            // Drawing the diameter with a green line, if available
//            if (diameterPoints[0] != null && diameterPoints[1] != null) {
//                GLUtil.drawLine(diameterPoints[0].x, diameterPoints[0].y, diameterPoints[1].x, diameterPoints[1].y, 0, 1, 0); // Green line
//            }

            // Drawing the enclosing circle if available
            if (circleCenter != null && circleRadius > 0) {
                // Assuming GLUtil.drawCircle can take radius as a parameter. Adjust if necessary.
                // Note: The color is set to a different one for distinction, let's say purple (1, 0, 1).
                GLUtil.drawCircle(new Circle(false, circleRadius), // Circle class might need to take diameter, hence radius * 2
                        circleCenter.getX(), circleCenter.getY(), 0,
                        1, 0, 1); // Purple
            }
        } catch (Exception e) {
            // It's generally a good practice to at least log exceptions.
            e.printStackTrace();
        }
    }

    public void add(Coordinates2D point){
        points.add(point);
        System.out.println("Added point: " + point.toString());
        onPointsUpdated();
    }

    public void undo(){
        points.remove(points.size()-1);
        onPointsUpdated();
    }

    public void removeClosestTo(Coordinates2D point){
        Coordinates2D nearest = Collections.min(points, new Comparator<Coordinates2D>(){
            @Override
            public int compare(Coordinates2D o1, Coordinates2D o2) {
                 return (int) (o1.distance(point) - o2.distance(point));
            }
        });
        points.remove(nearest);
        onPointsUpdated();
    }

    private void onPointsUpdated() {
//        hull = ConvexHull.makeHullFromCoordinates(points);
        computeEnclosingCircle();
        rfCenter = circleCenter;
//        rfCenter = getRFCenter();
//        computeDiameter(); // Update the diameter whenever points are updated
    }

    private void computeEnclosingCircle() {
        if (points.isEmpty()) {
            circleCenter = null;
            circleRadius = 0;
            return;
        }

        // Compute the center as the average of all points
        double sumX = 0, sumY = 0;
        for (Coordinates2D point : points) {
            sumX += point.getX();
            sumY += point.getY();
        }
        double centerX = sumX / points.size();
        double centerY = sumY / points.size();
        circleCenter = new Coordinates2D(centerX, centerY);

        // Compute the radius as the average distance to the points
        double sumDistance = 0;
        for (Coordinates2D point : points) {
            sumDistance += point.distance(circleCenter);
        }
        circleRadius = sumDistance / points.size();

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

//    public Coordinates2D getRFCenter(){
//        Point centroid = findCentroid(hull);
//        return point2Coordinates2D(centroid);
//    }
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


    public List<Coordinates2D> getPoints(){
        return points;
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
}