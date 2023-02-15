package org.xper.allen.ga;

import java.util.LinkedList;
import java.util.List;

public class Parent {
    Long id;
    Double spikeRate;

    public Parent(Long id, Double spikeRate) {
        this.id = id;
        this.spikeRate = spikeRate;
    }

    public static List<Parent> createParentListFrom(List<Long> ids, List<Double> spikeRates){
        List<Parent> parents = new LinkedList<>();
        for (int i=0; i<ids.size(); i++){
            parents.add(new Parent(ids.get(i), spikeRates.get(i)));
        }
        return parents;
    }

    Double percentile;


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

    public Double getPercentile() {
        return percentile;
    }

    public void setPercentile(Double percentile) {
        this.percentile = percentile;
    }
}
