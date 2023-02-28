package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.db.vo.ExpLogEntry;
import org.xper.db.vo.GenerationTaskDoneList;
import org.xper.db.vo.TaskDoneEntry;

import java.util.*;

public class MockParentSelector implements ParentSelector{


    @Dependency
    private MultiGaDbUtil dbUtil;

    @Dependency
    ParentAnalysisStrategy spikeRateAnalyzer;

    @Override
    public List<Long> selectParents(String gaName) {
        GenerationTaskDoneList taskDoneList = dbUtil.readTaskDoneForGaAndGeneration(gaName, dbUtil.readTaskDoneMaxGenerationIdForGa(gaName));

        List<TaskDoneEntry> doneTasks = taskDoneList.getDoneTasks();
        LinkedList<Long> previousGenerationIds = new LinkedList<>();
        for(TaskDoneEntry task:doneTasks){
            previousGenerationIds.add(task.getTaskId());
        }
        Collections.sort(previousGenerationIds);

        List<ExpLogEntry> expLogEntries = dbUtil.readExpLog(previousGenerationIds.getFirst(), previousGenerationIds.getLast());

        //for each entry in expLogEntries, read out the python dictionary
        HashMap<Long, Map<Integer, Double>> spikeRatesForStim = new HashMap<>();
        for (ExpLogEntry entry:expLogEntries){
            System.err.println(entry.getTstamp());
            String log = entry.getLog();
            HashMap<Integer, Double> spikeRatesForChannel = parsePythonDictionaryToHashMap(log);
            System.err.println(spikeRatesForChannel);
            spikeRatesForStim.put(entry.getTstamp(), spikeRatesForChannel);
        }

        System.out.println(spikeRatesForStim);

        //parse correct channel from spikeRatesForChannel and calculate spikeRates
        List<Double> spikeRates = new ArrayList<>();
        List<Long> parentIds = new ArrayList<>();
        spikeRatesForStim.forEach((k,v)->{
            spikeRates.add(v.get(1));
            parentIds.add(k);
        });
        System.out.println(spikeRates);
        //convert hashmap values into list
        List<Long> parents = spikeRateAnalyzer.selectParents(ParentData.createMapFrom(parentIds, spikeRates));
        return parents;
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

    public ParentAnalysisStrategy getSpikeRateAnalyzer() {
        return spikeRateAnalyzer;
    }

    public void setSpikeRateAnalyzer(ParentAnalysisStrategy spikeRateAnalyzer) {
        this.spikeRateAnalyzer = spikeRateAnalyzer;
    }
}
