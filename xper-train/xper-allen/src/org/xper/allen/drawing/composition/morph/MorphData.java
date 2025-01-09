package org.xper.allen.drawing.composition.morph;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MorphData {
    public Map<Integer, ComponentMorphData> dataForComps = new HashMap<>();
    public Map<Integer, String> typesForAddedComps = new HashMap<>();
    public List<Integer> removedComps = new ArrayList<>();
    public MorphData() {
    }

    public MorphData(MorphData toDeepCopy) {
        for (Map.Entry<Integer, ComponentMorphData> entry : toDeepCopy.getDataForComps().entrySet()) {
            dataForComps.put(entry.getKey(), new ComponentMorphData(entry.getValue()));
        }
        typesForAddedComps.putAll(toDeepCopy.typesForAddedComps);
        removedComps.addAll(toDeepCopy.removedComps);
    }

    public void addDataForComp(int compId, ComponentMorphData data){
        dataForComps.put(compId, data);
    }

    public void addAddedComp(int compId, int type){
        String typeString;
        if (type == 1){
            typeString = "E2E";
        }
        else if (type == 2){
            typeString = "E2J";
        }
        else if (type == 3){
            typeString = "E2B";
        }
        else if (type == 4){
            typeString = "B2E";
        }
        else{
            throw new IllegalArgumentException("Invalid type of limb addition");
        }
        typesForAddedComps.put(compId, typeString);
    }

    public void addRemovedComp(int i) {
        removedComps.add(i);
    }

    public Map<Integer, ComponentMorphData> getDataForComps() {
        return dataForComps;
    }

    public void setDataForComps(Map<Integer, ComponentMorphData> dataForComps) {
        this.dataForComps = dataForComps;
    }
}