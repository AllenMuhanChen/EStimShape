package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.db.vo.ExpLogEntry;

import java.util.*;

public class MockSpikeRateSource implements SpikeRateSource{

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    String gaName;

    @Override
    public Double getSpikeRate(Long stimId) {
        // Read all expLog entries
        long mostRecentTask = dbUtil.readTaskDoneMaxId();
        List<ExpLogEntry> expLogEntries = dbUtil.readExpLog(0, mostRecentTask);

        //Collect average spike rate across channels for each repetition
        Map<Long, List<Long>> taskDoneIdsForStimIds = dbUtil.readTaskDoneIdsForStimIds(gaName);
        List<Double> spikeRatesAcrossRepetitions = new LinkedList<>();
        for (ExpLogEntry entry: expLogEntries){
            double averageSpikeRateAcrossChannels = 0;
            if (taskDoneIdsForStimIds.get(stimId).contains(entry.getTstamp())){
                //parse spikeRatesAcrossRepetitions for each channel (key = channel, value = averageSpikeRateAcrossChannels)
                HashMap<Integer, Double> spikeRatesForChannel = parsePythonDictionaryToHashMap(entry.getLog());
                //average spikeRatesAcrossRepetitions for all channels
                for (Double rate: spikeRatesForChannel.values()){
                    averageSpikeRateAcrossChannels += rate;
                }
                averageSpikeRateAcrossChannels = averageSpikeRateAcrossChannels/spikeRatesForChannel.size();
            }
            spikeRatesAcrossRepetitions.add(averageSpikeRateAcrossChannels);
        }

        //average spikeRates across all repetitions
        double averageSpikeRate = 0;
        for (Double rate: spikeRatesAcrossRepetitions){
            averageSpikeRate += rate;
        }
        averageSpikeRate = averageSpikeRate/spikeRatesAcrossRepetitions.size();

        return averageSpikeRate;
    }


    public HashMap<Integer, Double> parsePythonDictionaryToHashMap (String pythonDictionary){
        HashMap<Integer, Double> map = new HashMap<>();
        //remove all curly braces
        pythonDictionary = pythonDictionary.replaceAll("[{ }]", "");
        String[] spikeRatePairs = pythonDictionary.split(",");


        for (String pair: spikeRatePairs){
            String[] pairArray = pair.split(":");
            map.put(Integer.parseInt(pairArray[0]), Double.parseDouble(pairArray[1]));
        }
        return map;
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public String getGaName() {
        return gaName;
    }

    public void setGaName(String gaName) {
        this.gaName = gaName;
    }
}