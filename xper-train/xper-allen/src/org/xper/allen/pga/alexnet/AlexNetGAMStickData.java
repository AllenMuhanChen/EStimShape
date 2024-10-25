package org.xper.allen.pga.alexnet;

import com.thoughtworks.xstream.XStream;
import org.xper.allen.drawing.composition.*;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

import javax.vecmath.Point3d;
import java.util.List;

public class AlexNetGAMStickData implements MStickData {
    AllenMStickSpec stickSpec;
    List<ShaftData> shaftData;
    List<TerminationData> terminationData;
    List<JunctionData> junctionData;
    AllenMStickSpec analysisStickSpec;
    Point3d massCenter;
    float[] light_position;
    RGBColor stimColor;
    Coordinates2D location;
    double sizeDiameter;
    String textureType;
    double contrast;

    public AlexNetGAMStickData() {
    }

    public AlexNetGAMStickData(List<ShaftData> shaftData, List<TerminationData> terminationData, List<JunctionData> junctionData, AllenMStickSpec mStickSpec, Point3d massCenter, float[] light_position, RGBColor stimColor, Coordinates2D location, double sizeDiameter, AllenMStickSpec stickSpec, String textureType, double contrast) {
        this.shaftData = shaftData;
        this.terminationData = terminationData;
        this.junctionData = junctionData;
        this.analysisStickSpec = mStickSpec;
        this.massCenter = massCenter;
        this.light_position = light_position;
        this.stimColor = stimColor;
        this.location = location;
        this.sizeDiameter = sizeDiameter;
        this.stickSpec = stickSpec;
        this.textureType = textureType;
        this.contrast = contrast;
    }

    static XStream s;

    static {
        s = new XStream();
        s = new XStream();
        s.alias("AllenMStickData", AllenMStickData.class);
        s.alias("TerminationData", TerminationData.class);
        s.alias("JunctionData", JunctionData.class);
        s.alias("ShaftData", ShaftData.class);
        s.alias("AllenMSickSpec", AllenMStickSpec.class);
    }

    static AlexNetGAMStickData fromXml(String xml) {
        return (AlexNetGAMStickData) s.fromXML(xml);
    }
    @Override
    public String toXml() {
        return AlexNetGAMStickData.toXml(this);
    }

    private static String toXml(AlexNetGAMStickData alexNetGAMStickData) {
        return s.toXML(alexNetGAMStickData);
    }

}