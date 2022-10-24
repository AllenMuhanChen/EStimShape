package org.xper.allen.nafc.blockgen;

import javax.media.j3d.Link;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.stream.IntStream;

public class TypeFrequency<Type> {

    private List<Type> types = new LinkedList<>();
    private List<Double> frequencies = new LinkedList<>();

    public TypeFrequency(List<Type> types, List<Double> frequencies) {
        this.types = types;
        this.frequencies = frequencies;
    }

    public TypeFrequency(){}


    public List<Type> getTrialList(int numTrials) {
        int[] typesNumTrials = new int[types.size()];
        for(int i=0; i<types.size(); i++) {
            typesNumTrials[i] = (int) Math.round(frequencies.get(i)* (double) numTrials);
        }
        if(IntStream.of(typesNumTrials).sum()!= numTrials) {
            throw new IllegalArgumentException("Total number of trials rounded from frequencies does not equal correct total num of trials");
        }

        List<Type> trialList = new LinkedList<>();
        for(int i = 0; i< types.size(); i++) {
            for (int j=0; j<typesNumTrials[i]; j++) {
                trialList.add(types.get(i));
            }
        }
        return trialList;
    }

    public List<Type> getShuffledTrialList(int numTrials){
        List<Type> trialList = getTrialList(numTrials);
        Collections.shuffle(trialList);
        return trialList;
    }

    public List<Type> getTypes() {
        return types;
    }

    public void setTypes(List<Type> types) {
        this.types = types;
    }

    public List<Double> getFrequencies() {
        return frequencies;
    }

    public void setFrequencies(List<Double> frequencies) {
        this.frequencies = frequencies;
    }

    public void add(Type type, Double frequency){
        types.add(type);
        this.frequencies.add(frequency);
    }
}
