package org.xper.allen.rfplot;

import com.thoughtworks.xstream.XStream;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.noisy.ConcaveHull;
import org.xper.allen.drawing.composition.noisy.ConcaveHull.Point;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.XMLizable;
import org.xper.utils.RGBColor;
import org.xper.rfplot.drawing.DefaultSpecRFPlotDrawable;

import javax.vecmath.Point3d;
import java.awt.geom.Line2D;
import java.awt.geom.Point2D;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class RFPlotMatchStick extends DefaultSpecRFPlotDrawable {
    public static final int NUM_POINTS_PER_COMPONENT = 10;
    AllenMatchStick matchStick;
    RFPlotMatchStickSpec spec;
    double sizeDiameterDegrees = 10;

    public RFPlotMatchStick() {
        setDefaultSpec();
    }

    @Override
    public void draw(Context context) {
        AllenMatchStick nextMStick = new AllenMatchStick();
        nextMStick.setProperties(spec.sizeDiameterDegrees, spec.texture);
        nextMStick.setStimColor(spec.color);
        nextMStick.genMatchStickFromShapeSpec(spec.getMStickSpec(), spec.getRotation());
        nextMStick.drawFast();
        matchStick.copyFrom(nextMStick);
    }

    @Override
    public void setSpec(String spec) {
        this.spec = RFPlotMatchStickSpec.fromXml(spec);
    }

    @Override
    public void setDefaultSpec() {
        matchStick = new AllenMatchStick();
        matchStick.setProperties(sizeDiameterDegrees, "SHADE");
        matchStick.genMatchStickRand();
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(matchStick, false);

        this.spec = new RFPlotMatchStickSpec(spec,
                sizeDiameterDegrees,
                new RGBColor(1, 0, 0),
                new double[]{0, 0, 0}, "SHADE");


    }

    @Override
    public String getSpec() {
        return spec.toXml();
    }

    public List<Coordinates2D> getProfilePoints(Coordinates2D mouseCoordinatesInDegrees) {
        int numComponents = matchStick.getNComponent();
        int totalPoints = NUM_POINTS_PER_COMPONENT * numComponents;

        // Calculate the angle from (0,0) to the mouse coordinates
        double angle = Math.atan2(mouseCoordinatesInDegrees.getY(), mouseCoordinatesInDegrees.getX());

        // Gather points to use for hull calculation
        ConcaveHull concaveHull = new ConcaveHull();
        ArrayList<Point3d> allMeshPoints = new ArrayList<>();
        for (int i = 1; i <= matchStick.getNComponent(); i++) {
            allMeshPoints.addAll(Arrays.asList(matchStick.getComp()[i].getVect_info()));
        }

        //Translate the mesh points by the mouse coordinates in degrees
        ArrayList<Point> translatedMeshPoints = new ArrayList<>();
        for (Point3d point : allMeshPoints) {
            if (point != null) {
                //Translate point by mouse Coordinates
                Point translatedPoint = new Point(point.x + mouseCoordinatesInDegrees.getX(), point.y + mouseCoordinatesInDegrees.getY());

                translatedMeshPoints.add(translatedPoint);
            }
        }
        //Calculate the hull
        ArrayList<Point> concaveHullPoints = concaveHull.calculateConcaveHull(translatedMeshPoints, 3);

        //Convert the hull points to Coordinates2D
        ArrayList<Coordinates2D> hullCoordinates = new ArrayList<>();
        for (Point point : concaveHullPoints) {
            //plot only numPoints points, distributed evenly
            int everyOther = concaveHullPoints.size() / totalPoints;
            if (concaveHullPoints.indexOf(point) % everyOther == 0) {
                hullCoordinates.add(new Coordinates2D(point.getX(), point.getY()));
            }
        }
        return hullCoordinates;
    }

    public static class RFPlotMatchStickSpec implements XMLizable {
        public AllenMStickSpec spec;
        public double sizeDiameterDegrees;
        public RGBColor color;
        public double[] rotation;
        public String texture;

        public RFPlotMatchStickSpec(AllenMStickSpec spec, double sizeDiameterDegrees, RGBColor color, double[] rotation, String texture) {
            this.spec = spec;
            this.sizeDiameterDegrees = sizeDiameterDegrees;
            this.color = color;
            this.rotation = rotation;
            this.texture = texture;
        }

        public RFPlotMatchStickSpec(RFPlotMatchStickSpec other) {
            this.spec = other.spec;
            this.sizeDiameterDegrees = other.sizeDiameterDegrees;
            this.color = other.color;
            this.rotation = other.rotation;
            this.texture = other.texture;
        }

        public RFPlotMatchStickSpec() {
        }

        static XStream s;

        static {
            s = new XStream();
            s.alias("StimSpec", RFPlotMatchStickSpec.class);
            s.useAttributeFor("animation", boolean.class);
        }

        public String toXml() {
            return s.toXML(this);
        }

        public static RFPlotMatchStickSpec fromXml(String spec) {
            return (RFPlotMatchStickSpec) s.fromXML(spec);
        }

        public AllenMStickSpec getMStickSpec() {
            return spec;
        }

        public void setSpec(AllenMStickSpec spec) {
            this.spec = spec;
        }

        public void setSpec(AllenMatchStick matchStick) {
            this.spec = new AllenMStickSpec();
            this.spec.setMStickInfo(matchStick, false);
        }

        public double getSizeDiameterDegrees() {
            return sizeDiameterDegrees;
        }

        public void setSizeDiameterDegrees(double sizeDiameterDegrees) {
            this.sizeDiameterDegrees = sizeDiameterDegrees;
        }

        public RGBColor getColor() {
            return color;
        }

        public void setColor(RGBColor color) {
            this.color = color;
        }

        public double[] getRotation() {
            return rotation;
        }

        public void setRotation(double[] rotation) {
            this.rotation = rotation;
        }

        public String getTexture() {
            return texture;
        }

        public void setTexture(String texture) {
            this.texture = texture;
        }

        @Override
        public XMLizable getFromXml(String xml) {
            return fromXml(xml);
        }
    }
}