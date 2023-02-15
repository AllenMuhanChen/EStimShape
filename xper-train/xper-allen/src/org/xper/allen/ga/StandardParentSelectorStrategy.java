package org.xper.allen.ga;

import java.util.*;
import java.util.function.BiConsumer;

public class StandardParentSelectorStrategy implements ParentSelectorStrategy {

    public static final LinkedHashMap<PercentileRange,Integer> NUMBER_OF_MORPHS_PER_RANGE = new LinkedHashMap<>();
    private List<Long> chosenStims = new ArrayList<>();
    static {
        NUMBER_OF_MORPHS_PER_RANGE.put(new PercentileRange(1.0, 0.9), 6);
        NUMBER_OF_MORPHS_PER_RANGE.put(new PercentileRange(0.9, 0.7), 4);
        NUMBER_OF_MORPHS_PER_RANGE.put(new PercentileRange(0.7, 0.5), 3);
        NUMBER_OF_MORPHS_PER_RANGE.put(new PercentileRange(0.5, 0.3), 2);
        NUMBER_OF_MORPHS_PER_RANGE.put(new PercentileRange(0.1, 0.0), 1);
    }
    @Override
    public List<Long> analyze(List<Parent> parents) {

        sortSpikesByAscending(parents);
        calculatePercentile(parents);
        chooseStimuli(parents);

        return chosenStims;
    }

    private void chooseStimuli(List<Parent> parents) {
        NUMBER_OF_MORPHS_PER_RANGE.forEach(new BiConsumer<PercentileRange, Integer>() {
            //For each PercentileRange-NumberStimuliToChoose
            //Choose the NumberStimuliToChoose from PercentileRange
           private List<Parent> parentsInPercentileRange;
           @Override
           public void accept(PercentileRange percentileRange, Integer numToChoose) {
               parentsInPercentileRange = new LinkedList<>();
               gatherWithinRangeStimuli(percentileRange);
               chooseRandomStimuli(numToChoose);
           }

            private void gatherWithinRangeStimuli(PercentileRange percentileRange) {
                for (Parent parent : parents){
                    if(parent.percentile <= percentileRange.top && parent.percentile > percentileRange.bottom){
                        parentsInPercentileRange.add(parent);
                    }
                }
            }

            private void chooseRandomStimuli(Integer numToChoose) {
                List<Parent> shuffleList = new LinkedList<>(parentsInPercentileRange);

                while(shuffleList.size() < numToChoose){
                    shuffleList.addAll(parentsInPercentileRange);
                }
                Collections.shuffle(shuffleList);

                for (int i = 0; i< numToChoose; i++){
                    chosenStims.add(shuffleList.get(i).getId());
                }
            }
       });
    }

    private void sortSpikesByAscending(List<Parent> spikeDataForStims) {
        spikeDataForStims.sort(new Comparator<Parent>() {
            @Override
            public int compare(Parent o1, Parent o2) {
                return (int) Math.round(o1.spikeRate-o2.spikeRate);
            }
        });
    }

    private void calculatePercentile(List<Parent> spikeStims) {
        int i=1;
        for (Parent stim : spikeStims) {
            int numStim = spikeStims.size();
            stim.percentile = ((double)i / numStim);
            i++;
        }
    }

    public static class PercentileRange {
        Double top;
        Double bottom;

        public PercentileRange(Double top, Double bottom) {
            this.top = top;
            this.bottom = bottom;
        }
    }


}


