package org.xper.allen.ga3d.blockgen;

import com.thoughtworks.xstream.XStream;

import java.util.LinkedHashMap;
import java.util.Map;

public class LineageData {
    public Map<Integer, Double> regimeScoreForGenerations = new LinkedHashMap<>();

    public LineageData() {
    }

    public void putRegimeScoreForGeneration(int generation, Double regimeScore) {
        regimeScoreForGenerations.put(generation, regimeScore);
    }

    static XStream s;

    static {
        s = new XStream();
        s.alias("LineageData", LineageData.class);
    }

    public String toXml() {
        return s.toXML(this);
    }

    public static LineageData fromXml(String xml) {
        return (LineageData) s.fromXML(xml);
    }

}