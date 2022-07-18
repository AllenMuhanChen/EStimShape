package org.xper.allen.nafc.blockgen;

import java.util.LinkedList;
import java.util.List;
import java.util.stream.IntStream;

public class BlockParam <Type> {

    private List<Type> types;
    private List<Double> typesFrequency;

    public BlockParam(List<Type> types, List<Double> typesFrequency) {
        this.types = types;
        this.typesFrequency = typesFrequency;
    }

    public List<Type> getTrialList(int numTrials) {
        int[] typesNumTrials = new int[types.size()];
        for(int i=0; i<types.size(); i++) {
            typesNumTrials[i] = (int) Math.round(typesFrequency.get(i)* (double) numTrials);
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
}
