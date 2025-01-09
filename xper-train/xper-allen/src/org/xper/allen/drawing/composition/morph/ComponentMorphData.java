package org.xper.allen.drawing.composition.morph;

import com.thoughtworks.xstream.XStream;

public class ComponentMorphData {
    public double orientationMagnitude;
    public double rotationMagnitude;
    public double lengthMagnitude;
    public double curvatureMagnitude;
    public double radiusProfileMagnitude;

    public ComponentMorphData(Double orientationMagnitude, Double rotationMagnitude, Double lengthMagnitude, Double curvatureMagnitude, Double radiusProfileMagnitude) {
        this.orientationMagnitude = orientationMagnitude;
        this.rotationMagnitude = rotationMagnitude;
        this.lengthMagnitude = lengthMagnitude;
        this.curvatureMagnitude = curvatureMagnitude;
        this.radiusProfileMagnitude = radiusProfileMagnitude;
    }

    public ComponentMorphData(ComponentMorphData toDeepCopy) {
        this.orientationMagnitude = toDeepCopy.orientationMagnitude;
        this.rotationMagnitude = toDeepCopy.rotationMagnitude;
        this.lengthMagnitude = toDeepCopy.lengthMagnitude;
        this.curvatureMagnitude = toDeepCopy.curvatureMagnitude;
        this.radiusProfileMagnitude = toDeepCopy.radiusProfileMagnitude;
    }

    static XStream xstream;

    static {
        xstream = new XStream();
        xstream.alias("NormalDistributedMorphData", ComponentMorphData.class);
    }

    public String toXml() {
        return xstream.toXML(this);
    }

    public static ComponentMorphData fromXml(String xml) {
        return (ComponentMorphData) xstream.fromXML(xml);
    }
}