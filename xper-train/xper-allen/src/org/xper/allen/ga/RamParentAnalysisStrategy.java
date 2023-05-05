package org.xper.allen.ga;

import java.util.*;
import java.util.function.BiConsumer;
import java.util.stream.Collectors;

public class RamParentAnalysisStrategy implements ParentAnalysisStrategy {

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
    public List<Long> selectParents(Map<Long, ? extends ParentData> dataForParents) {
        LinkedHashMap<Long, ? extends ParentData> sortedDataForParents = sortSpikesByAscending(new LinkedHashMap<>(dataForParents));
        Map<Long, Double> percentileForParents = calculatePercentile(sortedDataForParents);
        chooseParents(percentileForParents);

        return chosenParentIds;
    }

    private void chooseParents(Map<Long, Double> percentileForParents) {
        NUMBER_OF_MORPHS_PER_RANGE.forEach(
        new BiConsumer<PercentileRange, Integer>() {

            //For each PercentileRange-NumberStimuliToChoose
            //Choose the NumberStimuliToChoose from PercentileRange
           private List<Long> parentsInPercentileRange;
           @Override
           public void accept(PercentileRange percentileRange, Integer numToChoose) {
               parentsInPercentileRange = new LinkedList<>();
               gatherWithinPercentileStimuli(percentileRange);
               chooseRandomStimuli(numToChoose);
           }

            private void gatherWithinPercentileStimuli(PercentileRange percentileRange) {
                percentileForParents.forEach(new BiConsumer<Long, Double>() {
                    @Override
                    public void accept(Long stimId, Double percentile) {
                        if(percentile <= percentileRange.top && percentile > percentileRange.bottom){
                            parentsInPercentileRange.add(stimId);
                        }
                    }
                });
            }

            private void chooseRandomStimuli(Integer numToChoose) {
                List<Long> shuffleList = new LinkedList<>(parentsInPercentileRange);

                while(shuffleList.size() < numToChoose){
                    shuffleList.addAll(parentsInPercentileRange);
                }
                Collections.shuffle(shuffleList);

                for (int i = 0; i< numToChoose; i++){
                    chosenParentIds.add(shuffleList.get(i));
                }
            }
       });
    }

    private LinkedHashMap<Long, ? extends ParentData> sortSpikesByAscending(LinkedHashMap<Long, ? extends ParentData> dataForParents) {
        LinkedHashMap<Long, ? extends ParentData> sortedDataForParents = dataForParents.entrySet().stream().sorted(Map.Entry.comparingByValue(new Comparator<ParentData>() {
            @Override
            public int compare(ParentData o1, ParentData o2) {
                return (int) Math.round(o1.spikeRate - o2.spikeRate);
            }
        })).collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue, (e1, e2) -> e1, LinkedHashMap::new));

        return sortedDataForParents;
    }

    private Map<Long, Double> calculatePercentile(LinkedHashMap<Long, ? extends ParentData> dataForParents) {
        Map<Long, Double> percentileForParents = new LinkedHashMap<>();
        final int[] i = {1};
        int numStim = dataForParents.size();
        dataForParents.forEach(new BiConsumer<Long, ParentData>() {
            @Override
            public void accept(Long stimId, ParentData parentData) {
                percentileForParents.put(stimId, ((double) i[0] / numStim));
                i[0]++;
            }
        }
        );

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