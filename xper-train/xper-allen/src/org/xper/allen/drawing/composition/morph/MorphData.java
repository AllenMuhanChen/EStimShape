package org.xper.allen.drawing.composition.morph;

import java.util.HashMap;
import java.util.Map;

public class MorphData {
    public Map<Integer, ComponentMorphData> dataForComps = new HashMap<>();

    public MorphData() {
    }

    public MorphData(MorphData toDeepCopy) {
        for (Map.Entry<Integer, ComponentMorphData> entry : toDeepCopy.getDataForComps().entrySet()) {
            dataForComps.put(entry.getKey(), new ComponentMorphData(entry.getValue()));
        }
    }

    public void addDataForComp(int compId, ComponentMorphData data){
        dataForComps.put(compId, data);
    }

    public Map<Integer, ComponentMorphData> getDataForComps() {
        return dataForComps;
    }

    public void setDataForComps(Map<Integer, ComponentMorphData> dataForComps) {
        this.dataForComps = dataForComps;
    }
}