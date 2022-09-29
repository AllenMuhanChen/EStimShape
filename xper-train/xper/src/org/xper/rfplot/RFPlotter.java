package org.xper.rfplot;

import org.xper.drawing.Coordinates2D;

import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedList;
import java.util.List;

public class RFPlotter {

    List<Coordinates2D> points = new LinkedList<>();
    private List<Point> hull;

    public void add(Coordinates2D point){
        points.add(point);
        pointsUpdated();
    }

    public void undo(){
        points.remove(points.size()-1);
        pointsUpdated();
    }

    public void removeClosest(Coordinates2D to){
        Coordinates2D nearest = Collections.min(points, new Comparator<Coordinates2D>(){
            @Override
            public int compare(Coordinates2D o1, Coordinates2D o2) {
                 return (int) (o1.distance(to) - o2.distance(to));
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
