package org.xper.allen.newga.blockgen;

import com.thoughtworks.xstream.XStream;
import org.xper.allen.drawing.composition.*;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;

import java.util.List;

public class ExploreMStickData extends AllenMStickData {
    List<Integer> componentsExploring;

    public ExploreMStickData(AllenMStickData superData, List<Integer> componentsExploring) {
        super(superData);
        this.componentsExploring = componentsExploring;
    }

    public ExploreMStickData() {
    }

    static XStream s;

    static {
        s = new XStream();
        s.alias("AllenMStickData", ExploreMStickData.class);
        s.alias("TerminationData", TerminationData.class);
        s.alias("JunctionData", JunctionData.class);
        s.alias("ShaftData", ShaftData.class);
        s.alias("AllenMSickSpec", AllenMStickSpec.class);
    }

    public String toXml() {
        return ExploreMStickData.toXml(this);
    }

    public static String toXml(ExploreMStickData data){
        return s.toXML(data);
    }

    public static ExploreMStickData fromXml(String xml){
        return (ExploreMStickData) s.fromXML(xml);
    }

    public List<Integer> getComponentsExploring() {
        return componentsExploring;
    }

    public void setComponentsExploring(List<Integer> componentsExploring) {
        this.componentsExploring = componentsExploring;
    }

}