package org.xper.allen.ga;

import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class ParentData {
    Long id;
    Double spikeRate;

    public ParentData(Long id, Double spikeRate) {
        this.id = id;
        this.spikeRate = spikeRate;
    }

    public static List<ParentData> createParentListFrom(List<Long> ids, List<Double> spikeRates){
        List<ParentData> parentData = new LinkedList<>();
        for (int i=0; i<ids.size(); i++){
            parentData.add(new ParentData(ids.get(i), spikeRates.get(i)));
        }
        return parentData;
    }

    public static Map<Long, ParentData> createMapFrom(List<Long> ids, List<Double> spikeRates){
        Map<Long, ParentData> parentData = new LinkedHashMap<>();
        for (int i=0; i<ids.size(); i++){
            parentData.put(ids.get(i), new ParentData(ids.get(i), spikeRates.get(i)));
        }
        return parentData;
    }


    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Double getSpikeRate() {
        return spikeRate;
    }

    public void setSpikeRate(Double spikeRate) {
        this.spikeRate = spikeRate;
    }

}
