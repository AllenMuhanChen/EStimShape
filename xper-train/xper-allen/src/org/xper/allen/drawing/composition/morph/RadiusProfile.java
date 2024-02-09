package org.xper.allen.drawing.composition.morph;

import java.util.HashMap;
import java.util.Map;

public class RadiusProfile {
    Map<Integer, RadiusInfo> infoForRadius = new HashMap<>();

    //TODO: API to add radius info

    public Map<Integer, RadiusInfo> getInfoForRadius() {
        return infoForRadius;
    }

    public void addRadiusInfo(Integer id, RadiusInfo radiusInfo) {
        infoForRadius.put(id, radiusInfo);
    }

    public RadiusInfo getRadiusInfo(Integer id) {
        return infoForRadius.get(id);
    }
}