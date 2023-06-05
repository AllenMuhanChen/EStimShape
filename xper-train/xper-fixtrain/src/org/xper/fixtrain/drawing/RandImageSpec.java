package org.xper.fixtrain.drawing;

import com.thoughtworks.xstream.XStream;
import org.xper.drawing.Coordinates2D;

import java.io.File;

public class RandImageSpec {
    private File directory;

    private Coordinates2D dimensions;

    private String currentImgPath;


    public RandImageSpec() {
    }

    static XStream xstream;
    static
    {

        xstream = new XStream();
        xstream.alias("RandImageSpec", RandImageSpec.class);
    }

    public static RandImageSpec fromXml(String xml) {
        return (RandImageSpec) xstream.fromXML(xml);
    }

    public static String toXml(RandImageSpec msg) {
        return xstream.toXML(msg);
    }

    public String toXml() {
        return toXml(this);
    }


    public File getDirectory() {
        return directory;
    }

    public void setDirectory(File directory) {
        this.directory = directory;
    }

    public Coordinates2D getDimensions() {
        return dimensions;
    }

    public void setDimensions(Coordinates2D dimensions) {
        this.dimensions = dimensions;
    }

    public String getCurrentImgPath() {
        return currentImgPath;
    }

    public void setCurrentImgPath(String currentImgPath) {
        this.currentImgPath = currentImgPath;
    }
}