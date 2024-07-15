package org.xper.allen.drawing.composition.morph;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

public class RadiusProfile {
    Map<Integer, RadiusInfo> infoForRadius = new HashMap<>();

    public RadiusProfile(Map<Integer, RadiusInfo> infoForRadius) {
        this.infoForRadius = infoForRadius;
    }

    public RadiusProfile() {
    }

    public RadiusProfile(RadiusProfile other) {
        this.infoForRadius = new LinkedHashMap<>();
        for (Map.Entry<Integer, RadiusInfo> entry : other.infoForRadius.entrySet()) {
            this.infoForRadius.put(entry.getKey(), new RadiusInfo(entry.getValue()));
        }

    }

    public Map<Integer, RadiusInfo> getInfoForRadius() {
        return infoForRadius;
    }

    public void addRadiusInfo(Integer id, RadiusInfo radiusInfo) {
        infoForRadius.put(id, radiusInfo);
    }

    public RadiusInfo getRadiusInfo(Integer id) {
        return infoForRadius.get(id);
    }

    public String toString() {
        String str = "";
        for (Map.Entry<Integer, RadiusInfo> entry : infoForRadius.entrySet()) {
            str += entry.getKey() + ": " + entry.getValue().toString() + "\n";
        }
        return str;
    }
}