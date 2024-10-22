package org.xper.allen.drawing.composition;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamImplicitCollection;

import javax.vecmath.Point3d;
import java.io.BufferedWriter;
import java.io.FileWriter;
import java.util.List;

public class AllenMStickData implements MStickData {
    List<ShaftData> shaftData;
    List<TerminationData> terminationData;
    List<JunctionData> junctionData;
    AllenMStickSpec analysisMStickSpec;
    Point3d massCenter;

    static XStream s;

    static {
        s = new XStream();
        s.alias("AllenMStickData", AllenMStickData.class);
        s.alias("TerminationData", TerminationData.class);
        s.alias("JunctionData", JunctionData.class);
        s.alias("ShaftData", ShaftData.class);
        s.alias("AllenMSickSpec", AllenMStickSpec.class);
    }

    public AllenMStickData(AllenMStickData other) {
        this.shaftData = other.shaftData;
        this.terminationData = other.terminationData;
        this.junctionData = other.junctionData;
        this.analysisMStickSpec = other.analysisMStickSpec;
    }

    public AllenMStickData(List<ShaftData> shaftData, List<TerminationData> terminationData, List<JunctionData> junctionData, AllenMStickSpec analysisMStickSpec) {
        this.shaftData = shaftData;
        this.terminationData = terminationData;
        this.junctionData = junctionData;
        this.analysisMStickSpec = analysisMStickSpec;
    }

    public AllenMStickData() {
    }

    public String toXml() {
        return AllenMStickData.toXml(this);
    }

    public static String toXml(AllenMStickData data){
        return s.toXML(data);
    }

    public void writeInfo2File(String fname){
        try {
            BufferedWriter out = new BufferedWriter(new FileWriter(fname + "_spec.xml"));
            out.write(toXml());
            out.flush();
            out.close();
        } catch (Exception e) {
            System.out.println(e);
        }
    }

    public List<ShaftData> getShaftData() {
        return shaftData;
    }

    public void setShaftData(List<ShaftData> shaftData) {
        this.shaftData = shaftData;
    }

    public List<TerminationData> getTerminationData() {
        return terminationData;
    }

    public void setTerminationData(List<TerminationData> terminationData) {
        this.terminationData = terminationData;
    }

    public List<JunctionData> getJunctionData() {
        return junctionData;
    }

    public void setJunctionData(List<JunctionData> junctionData) {
        this.junctionData = junctionData;
    }

    public AllenMStickSpec getAnalysisMStickSpec() {
        return analysisMStickSpec;
    }

    public void setAnalysisMStickSpec(AllenMStickSpec analysisMStickSpec) {
        this.analysisMStickSpec = analysisMStickSpec;
    }

    @Override
    public String toString() {
        return "AllenMStickData{" +
                "shaftData=" + shaftData +
                ", terminationData=" + terminationData +
                ", junctionData=" + junctionData +
                ", analysisMStickSpec=" + analysisMStickSpec +
                '}';
    }

    public Point3d getMassCenter() {
        return massCenter;
    }

    public void setMassCenter(Point3d massCenter) {
        this.massCenter = massCenter;
    }
}