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

    List<Coordinates2D> points = new LinkedList<>();
    private List<Point> hull;


    public void draw(){
        try {
            for (Coordinates2D point : points) {
                GLUtil.drawCircle(new Circle(true, 5), point.getX(), point.getY(), 0, 1, 1, 0);
            }

            for (Point point : hull) {
                GLUtil.drawCircle(new Circle(true, 5), point.x, point.y, 0, 1, 0, 0);
            }
            Coordinates2D rfCenter = getRFCenter();
            GLUtil.drawSquare(new Square(true, 10), rfCenter.getX(), rfCenter.getY(), 0, 0, 1, 1);
        } catch (Exception e){}
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
    }

    public Coordinates2D getRFCenter(){
        Point centroid = findCentroid(hull);
        return new Coordinates2D(centroid.x, centroid.y);
    }

    public List<Point> getHull(){
        return hull;
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
