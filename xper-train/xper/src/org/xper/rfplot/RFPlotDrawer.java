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

    private final List<Coordinates2D> points = new LinkedList<>();
    private List<Point> hull;
    private Coordinates2D rfCenter;


    public void draw() {
        try {
            // Drawing the regular points as yellow circles
            for (Coordinates2D point : points) {
                GLUtil.drawCircle(new Circle(true, 5), point.getX(), point.getY(), 0, 1, 1, 0);
            }

            // Drawing the hull points as red circles
            if (hull != null && !hull.isEmpty()) {
                for (Point hullPoint : hull) {
                    GLUtil.drawCircle(new Circle(true, 5), hullPoint.x, hullPoint.y, 0, 1, 0, 0);
                }
            }

            // Drawing the hull as a polygon
            if (hull != null && !hull.isEmpty()) {
                int hullSize = hull.size();
                for (int i = 0; i < hullSize; i++) {
                    Point start = hull.get(i);
                    Point end = hull.get((i + 1) % hullSize); // Ensures the last point connects back to the first
                    GLUtil.drawLine(start.x, start.y, end.x, end.y, 1, 0, 0); // Replace with actual line drawing method
                }
            }

            // Drawing the RF center as a square
            GLUtil.drawSquare(new Square(true, 10), rfCenter.getX(), rfCenter.getY(), 0, 0, 1, 1);
        } catch (Exception e) {
        }
    }
    public void add(Coordinates2D point){
        points.add(point);
        pointsUpdated();
    }

    public void undo(){
        points.remove(points.size()-1);
        pointsUpdated();
    }

    public void removeClosestTo(Coordinates2D point){
        Coordinates2D nearest = Collections.min(points, new Comparator<Coordinates2D>(){
            @Override
            public int compare(Coordinates2D o1, Coordinates2D o2) {
                 return (int) (o1.distance(point) - o2.distance(point));
            }
        });
    points.remove(nearest);
    pointsUpdated();
    }

    private void pointsUpdated() {
        hull = ConvexHull.makeHullFromCoordinates(points);
        rfCenter = getRFCenter();
    }

    public Coordinates2D getRFCenter(){
        Point centroid = findCentroid(hull);
        return point2Coordinates2D(centroid);
    }

    public List<Coordinates2D> getHull(){
        List<Coordinates2D> hullCoords = pointsToCoords(hull);
        return hullCoords;
    }

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
}