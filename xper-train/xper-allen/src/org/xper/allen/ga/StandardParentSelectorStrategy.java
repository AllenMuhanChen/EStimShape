package org.xper.allen.ga;

import java.util.*;
import java.util.function.BiConsumer;

public class StandardParentSelectorStrategy implements ParentSelectorStrategy {

    public static final LinkedHashMap<PercentileRange,Integer> NUMBER_OF_MORPHS_PER_RANGE = new LinkedHashMap<>();
    private List<Long> chosenParentIds = new ArrayList<>();
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
        Map<Parent, Double> percentileForParents = calculatePercentile(parents);
        chooseParents(percentileForParents);

        return chosenParentIds;
    }

    private void chooseParents(Map<Parent, Double> percentileForParents) {
        NUMBER_OF_MORPHS_PER_RANGE.forEach(
        new BiConsumer<PercentileRange, Integer>() {

            //For each PercentileRange-NumberStimuliToChoose
            //Choose the NumberStimuliToChoose from PercentileRange
           private List<Parent> parentsInPercentileRange;
           @Override
           public void accept(PercentileRange percentileRange, Integer numToChoose) {
               parentsInPercentileRange = new LinkedList<>();
               gatherWithinPercentileStimuli(percentileRange);
               chooseRandomStimuli(numToChoose);
           }

            private void gatherWithinPercentileStimuli(PercentileRange percentileRange) {
                percentileForParents.forEach(new BiConsumer<Parent, Double>() {
                    @Override
                    public void accept(Parent parent, Double percentile) {
                        if(percentile <= percentileRange.top && percentile > percentileRange.bottom){
                            parentsInPercentileRange.add(parent);
                        }
                    }
                });
            }

            private void chooseRandomStimuli(Integer numToChoose) {
                List<Parent> shuffleList = new LinkedList<>(parentsInPercentileRange);

                while(shuffleList.size() < numToChoose){
                    shuffleList.addAll(parentsInPercentileRange);
                }
                Collections.shuffle(shuffleList);

                for (int i = 0; i< numToChoose; i++){
                    chosenParentIds.add(shuffleList.get(i).getId());
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

    private Map<Parent, Double> calculatePercentile(List<Parent> spikeStims) {
        Map<Parent, Double> percentileForParents = new LinkedHashMap<>();
        int i=1;
        for (Parent stim : spikeStims) {
            int numStim = spikeStims.size();
            percentileForParents.put(stim, ((double)i / numStim));
            i++;
        }
        return percentileForParents;
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


