package org.xper.allen.ga;

import java.util.*;
import java.util.function.BiConsumer;

public class StandardSpikeRateAnalyzer implements SpikeRateAnalyzer {

    public static final LinkedHashMap<PercentileRange,Integer> NUMBER_OF_MORPHS_PER_RANGE = new LinkedHashMap<>();
    private List<Long> chosenStims;
    static {
        NUMBER_OF_MORPHS_PER_RANGE.put(new PercentileRange(1.0, 0.9), 6);
        NUMBER_OF_MORPHS_PER_RANGE.put(new PercentileRange(0.9, 0.7), 4);
        NUMBER_OF_MORPHS_PER_RANGE.put(new PercentileRange(0.7, 0.5), 3);
        NUMBER_OF_MORPHS_PER_RANGE.put(new PercentileRange(0.5, 0.3), 2);
        NUMBER_OF_MORPHS_PER_RANGE.put(new PercentileRange(0.1, 0.0), 1);
    }
    @Override
    public List<Long> analyze(List<Long> stimIds, List<Double> spikeRates) {
        chosenStims = new LinkedList<>();
       List<Stim> spikeDataForStims = new ArrayList<>();
        for (int i=0; i<stimIds.size(); i++){
            spikeDataForStims.add(new Stim(stimIds.get(i), spikeRates.get(i)));
        }

        sortSpikesByAscending(spikeDataForStims);
        calculatePercentile(spikeDataForStims);
        chooseStimuli(spikeDataForStims);

        return chosenStims;
    }

    private void chooseStimuli(List<Stim> spikeDataForStims) {
        NUMBER_OF_MORPHS_PER_RANGE.forEach(new BiConsumer<PercentileRange, Integer>() {
            //For each PercentileRange-NumberStimuliToChoose
            //Choose the NumberStimuliToChoose from PercentileRange
           private List<Stim> stimsInPercentileRange;
           @Override
           public void accept(PercentileRange percentileRange, Integer numToChoose) {
               stimsInPercentileRange = new LinkedList<>();
               gatherWithinRangeStimuli(percentileRange);
               chooseRandomStimuli(numToChoose);
           }

            private void gatherWithinRangeStimuli(PercentileRange percentileRange) {
                for (Stim stim : spikeDataForStims){
                    if(stim.percentile <= percentileRange.top && stim.percentile > percentileRange.bottom){
                        stimsInPercentileRange.add(stim);
                    }
                }
            }

            private void chooseRandomStimuli(Integer numToChoose) {
                List<Stim> shuffleList = new LinkedList<>(stimsInPercentileRange);

                while(shuffleList.size() < numToChoose){
                    shuffleList.addAll(stimsInPercentileRange);
                }
                Collections.shuffle(shuffleList);

                for (int i = 0; i< numToChoose; i++){
                    chosenStims.add(shuffleList.get(i).getId());
                }
            }
       });
    }

    private void sortSpikesByAscending(List<Stim> spikeDataForStims) {
        spikeDataForStims.sort(new Comparator<Stim>() {
            @Override
            public int compare(Stim o1, Stim o2) {
                return (int) Math.round(o1.spikeRate-o2.spikeRate);
            }
        });
    }

    private void calculatePercentile(List<Stim> spikeStims) {
        int i=1;
        for (Stim stim : spikeStims) {
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


    public static class Stim {
        Long id;
        Double spikeRate;

        public Stim(Long id, Double spikeRate) {
            this.id = id;
            this.spikeRate = spikeRate;
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

}


