package org.xper.fixtrain.drawing;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.Coordinates2D;

public class ImageSpec {
    Coordinates2D center;
    Coordinates2D dimensions;
    String path;
    double alpha = 1;

    public ImageSpec(Coordinates2D center, Coordinates2D dimensions, String path, double alpha) {
        this.center = center;
        this.dimensions = dimensions;
        this.path = path;
        this.alpha = alpha;
    }

    public ImageSpec(Coordinates2D center, Coordinates2D dimensions, String path) {
        this.center = center;
        this.dimensions = dimensions;
        this.path = path;
    }

    public ImageSpec() {

    }

    transient static XStream s;

    static {
        s = new XStream();
        s.alias("StimSpec", ImageSpec.class);
    }

    public String toXml () {
        return s.toXML(this);
    }

    public static ImageSpec fromXml (String xml) {
//		System.out.println(xml);
        ImageSpec p = (ImageSpec)s.fromXML(xml);
        return p;
    }

    public Coordinates2D getCenter() {
        return center;
    }

    public void setCenter(Coordinates2D center) {
        this.center = center;
    }

    public String getPath() {
        return path;
    }

    public void setPath(String path) {
        this.path = path;
    }

    public Coordinates2D getDimensions() {
        return dimensions;
    }
    public void setDimensions(Coordinates2D dimensions) {
        this.dimensions = dimensions;
    }

    public double getAlpha() {
        return alpha;
    }

    public void setAlpha(double alpha) {
        this.alpha = alpha;
    }

}