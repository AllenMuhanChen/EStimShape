package org.xper.rfplot;

import org.xper.drawing.Coordinates2D;
import org.xper.drawing.GLUtil;
import org.xper.drawing.RGBColor;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.Square;


import java.util.*;

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
            GLUtil.drawCircle(new Circle(false, circleRadius), // Circle class might need to take diameter, hence radius * 2
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
            GLUtil.drawCircle(new Circle(true, 5), point.getX(), point.getY(), 0, color.getRed(), color.getGreen(), color.getBlue()); // Yellow
        }
    }



    private void onPointsUpdated() {
//        hull = ConvexHull.makeHullFromCoordinates(points);
        computeEnclosingCircle();
        rfCenter = rfsForChannels.get(currentChannel).getCircleCenter();
//        rfCenter = getRFCenter();
//        computeDiameter(); // Update the diameter whenever points are updated
    }

    private void computeEnclosingCircle() {
        List<Coordinates2D> circlePoints = rfsForChannels.get(currentChannel).getCirclePoints();
        double circleRadius = rfsForChannels.get(currentChannel).getCircleRadius();
        Coordinates2D circleCenter;
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
        rfsForChannels.get(currentChannel).setCircleCenter(circleCenter);
        rfsForChannels.get(currentChannel).setCircleRadius(circleRadius);
    }

    public Coordinates2D getRFCenter(){
        return rfsForChannels.get(currentChannel).getCircleCenter();
    }


    public List<Coordinates2D> getInterpolatedOutline() {
        Coordinates2D circleCenter = rfsForChannels.get(currentChannel).getCircleCenter();
        double circleRadius = rfsForChannels.get(currentChannel).getCircleRadius();

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

    public Map<String, RGBColor> getColorsForChannels() {
        return colorsForChannels;
    }
}