package org.xper.allen.ga;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.xper.Dependency;
import org.xper.allen.ga.regimescore.LineageMaxResponseSource;
import org.xper.allen.ga.regimescore.MutationType;
import org.xper.allen.ga.regimescore.RegimeScoreSource;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.allen.util.TikTok;

import java.util.*;
import java.util.function.BiConsumer;

/**
 * Calculates regime score and then uses that regime score to:
 *  1. assigns slots to lineages.
 *  2. then assigns those slots to specific regimes.
 *
 */
public class SlotSelectionProcess {
    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    Integer numChildrenToSelect;

    @Dependency
    RegimeScoreSource regimeScoreSource;

    @Dependency
    Integer maxLineagesToBuild;

    /**
     * Function that maps regime score of a linaege to likelihood of assigning slots to that lineage.
     */
    @Dependency
    UnivariateRealFunction slotFunctionForLineage;

    /**
     * A separate function for each regime that maps regime score to likelihood of slots being
     * assigned to that regime.
     */
    @Dependency
    Map<MutationType, UnivariateRealFunction> slotFunctionForRegimes;

    /**
     * Once slots are assigned to lineages and regimes, this function maps the response rate of a parent
     * to likelihood that the parent should be selected based on the regime.
     */
    @Dependency
    Map<MutationType, UnivariateRealFunction> fitnessFunctionForRegimes;

    @Dependency
    SpikeRateSource spikeRateSource;

    @Dependency
    LineageMaxResponseSource maxResponseSource;



    public List<Child> select(String gaName) {
        List<Child> selectedParents = new LinkedList<>();

        System.out.println("Fetching Lineage Ids");
        TikTok lineageTimer = new TikTok("Fetching Lineage Ids");
        List<Long> lineageIds = chooseLineages(gaName);
        lineageTimer.stop();

        System.out.println("Calculating Regime Scores");
        TikTok regimeScoreTimer = new TikTok("Calculating Regime Scores");
        Map<Long, Double> regimeScoreForLineages =
                calculateRegimeScoresForLineages(lineageIds);
        regimeScoreTimer.stop();

        System.out.println("Creating Slots For Lineages");
        TikTok slotTimer = new TikTok("Creating Slots For Lineages");
        Map<Long, List<Slot>> slotsForLineages =
                createSlotsForLineages(regimeScoreForLineages);
        slotTimer.stop();

        System.out.println("Assigning Regimes To Slots");
        TikTok regimeTimer = new TikTok("Assigning Regimes To Slots");
        assignRegimesToSlotsForEachLineage(slotsForLineages, regimeScoreForLineages);
        regimeTimer.stop();

        // For Each slot, use the lineage to choose parents, and use the regime to assign fitness score
        System.out.println("Assigning Fitness Scores To Slots");
        TikTok fitnessTimer = new TikTok("Assigning Fitness Scores To Slots");
        fillSlotsWithParents(gaName, selectedParents, slotsForLineages);
        fitnessTimer.stop();
        return selectedParents;
    }

    /**
     * Count how many lineages are past regime score of 1.0.
     * If the amount is less than maxLineagesToBuild, then return all lineages,
     * so we can have more lineages reach regime score of 1.0.
     *
     * If the amount is greater or equal to maxLineagesToBuild, then
     * return the top maxLineagesToBuild lineages.
     * @param gaName
     * @return
     */
    private List<Long> chooseLineages(String gaName) {
        List<Long> allLineageIds =  dbUtil.readAllLineageIds(gaName);

        // Read regime scores for all lineages
        Map<Long, Double> regimeScoresForLineageIds = new LinkedHashMap<>();
        for (long lineageId: allLineageIds) {
            Double currentRegimeScore = dbUtil.readRegimeScore(lineageId);
            regimeScoresForLineageIds.put(lineageId, currentRegimeScore);
        }

        boolean reachedMaxLineagesToBuild = reachedMaxLineagesToBuild(regimeScoresForLineageIds);

        if (!reachedMaxLineagesToBuild) {
            return allLineageIds;
        }
        else{
            return chooseTopLineages(regimeScoresForLineageIds);
        }


    }

    private boolean reachedMaxLineagesToBuild(Map<Long, Double> regimeScoresForLineageIds) {
        // Count number of lineages with regimeScore >= 1.0
        int numRegimeOnePlusLineages = 0;
        for (Double regimeScore: regimeScoresForLineageIds.values()) {
            if (regimeScore >= 1.0) {
                numRegimeOnePlusLineages++;
            }
        }
        return numRegimeOnePlusLineages >= maxLineagesToBuild;
    }

    private List<Long> chooseTopLineages(Map<Long, Double> regimeScoresForLineageIds) {
        // Sort lineages by regime score descending
        List<Map.Entry<Long, Double>> lineageIdAndRegimeScoreList =
                new LinkedList<>(regimeScoresForLineageIds.entrySet());
        Collections.sort(lineageIdAndRegimeScoreList, new Comparator<Map.Entry<Long, Double>>() {
            @Override
            public int compare(Map.Entry<Long, Double> o1, Map.Entry<Long, Double> o2) {
                return o2.getValue().compareTo(o1.getValue());
            }
        });

        // Get the top maxLineagesToBuild lineages
        List<Long> topLineageIds = new LinkedList<>();
        for (int i = 0; i < maxLineagesToBuild; i++) {
            topLineageIds.add(lineageIdAndRegimeScoreList.get(i).getKey());
        }
        return topLineageIds;
    }

    private List<Long> treeSpecsToLineageIds(List<String> treeSpecs) {
        List<Long> founderIds = new LinkedList<>();
        for (String treeSpec : treeSpecs) {
            Branch<Long> tree = Branch.fromXml(treeSpec);
            founderIds.add(tree.getIdentifier());
        }
        return founderIds;
    }

    private Map<Long, Double> calculateRegimeScoresForLineages(List<Long> lineageIds) {
        // Calculate Regime Scores For All Lineages
        Map<Long, Double> regimeScoreForLineages = new LinkedHashMap<>();
        for (Long lineageId : lineageIds){
            TikTok regimeScoreTimer = new TikTok("Calculating Regime Score For Lineage: " + lineageId);
            regimeScoreForLineages.put(lineageId, regimeScoreSource.getLineageScore(lineageId));
            regimeScoreTimer.stop();
        }
        return regimeScoreForLineages;
    }

    private Map<Long, List<Slot>> createSlotsForLineages(Map<Long, Double> regimeScoreForLineages) {

        Map<Long, Double> slotScoresForLineages =
                calculateSlotScoresForLineages(regimeScoreForLineages);

        ProbabilityTable<Long> probabilitiesForLineageIds =
                new ProbabilityTable<>(slotScoresForLineages);

        return drawLineagesForSlotsFromTable(probabilitiesForLineageIds);
    }

    private void assignRegimesToSlotsForEachLineage(Map<Long, List<Slot>> slotsForLineages, Map<Long, Double> regimeScoreForLineages) {
        slotsForLineages.forEach(new BiConsumer<Long, List<Slot>>() {
            @Override
            public void accept(Long lineageId, List<Slot> slots) {
                Double regimeScore = regimeScoreForLineages.get(lineageId);
                assignRegimes(slots, regimeScore);
            }
        });
    }

    private void fillSlotsWithParents(String gaName, List<Child> selectedParents, Map<Long, List<Slot>> slotsForLineages) {
        slotsForLineages.forEach(new BiConsumer<Long, List<Slot>>() {
            @Override
            public void accept(Long lineageId, List<Slot> slots) {
                TikTok assignSlotsTimer = new TikTok("Assigning Slots For Lineage: " + lineageId + " with " + slots.size() + " slots");

                for (Slot slot : slots) {;
                    // use lineageId to find potential parents
                    TikTok findPotentialParentsTimer = new TikTok("Using lineageId: " + lineageId + " to find potential parents");
                    List<Long> potentialParents = dbUtil.readDoneStimIdsFromLineage(gaName, lineageId);
                    findPotentialParentsTimer.stop();

                    // find normalized normalizedResponses for each potential parents
                    TikTok normalizedResponseTimer = new TikTok("Finding normalized responses for each potential parent");
                    List<Double> normalizedResponses = new LinkedList<>();
                    for (Long potentialParent : potentialParents) {
                        TikTok spikeRateTimer = new TikTok("Getting spike rate for potential parent: " + potentialParent);
                        Double averageSpikeRate = spikeRateSource.getSpikeRate(potentialParent);
                        spikeRateTimer.stop();
                        double normalizedSpikeRate = averageSpikeRate / maxResponseSource.getValue(lineageId);
                        normalizedResponses.add(normalizedSpikeRate);
                    }
                    normalizedResponseTimer.stop();

                    // use normalizedResponses to find fitness scores
                    TikTok fitnessScoreTimer = new TikTok("Using normalized responses to find fitness scores");
                    List<Double> fitnessScores = new LinkedList<>();
                    for (Double response : normalizedResponses) {
                        fitnessScores.add(plugIntoFunction(fitnessFunctionForRegimes.get(slot.getRegime()), response));
                    }
                    fitnessScoreTimer.stop();


                    // use fitnessFunctions and normalizedResponses to assign fitness scores to each potential parent
                    //slow
                    TikTok probabilityTableTimer = new TikTok("Using fitness functions and normalized responses to assign fitness scores to each potential parent");
                    ProbabilityTable<Long> probabilitiesForParentIds = new ProbabilityTable<>(potentialParents, fitnessScores);
                    probabilityTableTimer.stop();

                    // select parents
                    TikTok selectingParentsTimer = new TikTok("Selecting parents");
                    selectedParents.add(new Child(probabilitiesForParentIds.sampleWithReplacement(), slot.getRegime(),1.0 ));
                    selectingParentsTimer.stop();

                }
                assignSlotsTimer.stop();
            }
        });
    }

    private void assignRegimes(List<Slot> slotsForLineage, Double regimeScore) {
        Integer numSlotsForLineage = slotsForLineage.size();

        //calculate how many slotsForLineage to assign to each regime
        Map<MutationType, Integer> numSlotsForRegimes = assignNumSlotsToRegimes(regimeScore, numSlotsForLineage);

        //populate slotsForLineage for regimes
        Iterator<Slot> slotsIterator = slotsForLineage.iterator();
        for (MutationType mutationType : numSlotsForRegimes.keySet()) {
            int numSlotsAssigned = 0;
            while(numSlotsAssigned < numSlotsForRegimes.get(mutationType)) {
                slotsIterator.next().setRegime(mutationType);
                numSlotsAssigned++;
            }

        }
    }

    private Double calculateAverageSpikeRate(List<Double> spikeRates) {
        Double sum = 0.0;
        for (Double spikeRate : spikeRates) {
            sum += spikeRate;
        }
        return sum / spikeRates.size();
    }

    private Map<Long, Double> calculateSlotScoresForLineages(Map<Long, Double> regimeScoreForLineages) {
        Map<Long, Double> slotScoresForLineages = new LinkedHashMap<>();
        for (Long lineageId : regimeScoreForLineages.keySet()) {
            Double regimeScore = regimeScoreForLineages.get(lineageId);
            Double slotScore = plugIntoFunction(slotFunctionForLineage, regimeScore);
            slotScoresForLineages.put(lineageId, slotScore);
        }
        return slotScoresForLineages;
    }

    private Map<Long, List<Slot>> drawLineagesForSlotsFromTable(ProbabilityTable<Long> probabilitiesForLineageIds) {
        Map<Long, List<Slot>> slotsForLineages = new LinkedHashMap<>();
        for (int i = 0; i < numChildrenToSelect; i++) {
            Long lineageId = probabilitiesForLineageIds.sampleWithReplacement();
            List<Slot> slotsForLineage = slotsForLineages.get(lineageId);
            if (slotsForLineage == null) {
                slotsForLineage = new LinkedList<>();
                slotsForLineages.put(lineageId, slotsForLineage);
            }
            slotsForLineage.add(new Slot(lineageId));
        }
        return slotsForLineages;
    }

    private Map<MutationType, Integer> assignNumSlotsToRegimes(Double regimeScore, Integer numSlotsForLineage) {
        Map<MutationType, Double> slotScoreForRegimes = calculateSlotScoresForRegimes(regimeScore);

        ProbabilityTable<MutationType> probabilitiesForRegimes =
                new ProbabilityTable<>(slotScoreForRegimes);

        return drawSlotsForRegimes(probabilitiesForRegimes, numSlotsForLineage);
    }

    private Map<MutationType, Double> calculateSlotScoresForRegimes(Double regimeScore) {
        Map<MutationType, Double> slotScoreForRegimes = new LinkedHashMap<>();
        for (MutationType mutationType : slotFunctionForRegimes.keySet()) {
            UnivariateRealFunction slotFunction = slotFunctionForRegimes.get(mutationType);
            Double slotScore = plugIntoFunction(slotFunction, regimeScore);
            slotScoreForRegimes.put(mutationType, slotScore);
        }
        return slotScoreForRegimes;
    }

    private Map<MutationType, Integer> drawSlotsForRegimes(ProbabilityTable<MutationType> probabilitiesForRegimes, Integer numSlotsForLineage) {
        Map<MutationType, Integer> numSlotsForRegimes = new LinkedHashMap<>();
        for (int i = 0; i < numSlotsForLineage; i++) {
            MutationType mutationType = probabilitiesForRegimes.sampleWithReplacement();
            numSlotsForRegimes.putIfAbsent(mutationType, 0);
            Integer numSlotsForRegime = numSlotsForRegimes.get(mutationType);
            numSlotsForRegimes.put(mutationType, numSlotsForRegime + 1);
        }
        return numSlotsForRegimes;
    }

    private Double plugIntoFunction(UnivariateRealFunction slotFunction, Double regimeScore) {
        Double proportion = null;
        try {
            proportion = slotFunction.value(regimeScore);
        } catch (FunctionEvaluationException e) {
            throw new RuntimeException(e);
        }
        return proportion;
    }




    public static class Slot {
        private Long lineageId;
        private MutationType mutationType;

        public Slot(Long lineageId) {
            this.lineageId = lineageId;
        }

        public Long getLineageId() {
            return lineageId;
        }

        public void setLineageId(Long lineageId) {
            this.lineageId = lineageId;
        }

        public MutationType getRegime() {
            return mutationType;
        }

        public void setRegime(MutationType mutationType) {
            this.mutationType = mutationType;
        }
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public Integer getNumChildrenToSelect() {
        return numChildrenToSelect;
    }

    public void setNumChildrenToSelect(Integer numChildrenToSelect) {
        this.numChildrenToSelect = numChildrenToSelect;
    }

    public RegimeScoreSource getRegimeScoreSource() {
        return regimeScoreSource;
    }

    public void setRegimeScoreSource(RegimeScoreSource regimeScoreSource) {
        this.regimeScoreSource = regimeScoreSource;
    }

    public UnivariateRealFunction getSlotFunctionForLineage() {
        return slotFunctionForLineage;
    }

    public void setSlotFunctionForLineage(UnivariateRealFunction slotFunctionForLineage) {
        this.slotFunctionForLineage = slotFunctionForLineage;
    }

    public Map<MutationType, UnivariateRealFunction> getSlotFunctionForRegimes() {
        return slotFunctionForRegimes;
    }

    public void setSlotFunctionForRegimes(Map<MutationType, UnivariateRealFunction> slotFunctionForRegimes) {
        this.slotFunctionForRegimes = slotFunctionForRegimes;
    }

    public Map<MutationType, UnivariateRealFunction> getFitnessFunctionForRegimes() {
        return fitnessFunctionForRegimes;
    }

    public void setFitnessFunctionForRegimes(Map<MutationType, UnivariateRealFunction> fitnessFunctionForRegimes) {
        this.fitnessFunctionForRegimes = fitnessFunctionForRegimes;
    }

    public SpikeRateSource getSpikeRateSource() {
        return spikeRateSource;
    }

    public void setSpikeRateSource(SpikeRateSource spikeRateSource) {
        this.spikeRateSource = spikeRateSource;
    }

    public LineageMaxResponseSource getMaxResponseSource() {
        return maxResponseSource;
    }

    public void setMaxResponseSource(LineageMaxResponseSource maxResponseSource) {
        this.maxResponseSource = maxResponseSource;
    }

    public Integer getMaxLineagesToBuild() {
        return maxLineagesToBuild;
    }

    public void setMaxLineagesToBuild(Integer maxLineagesToBuild) {
        this.maxLineagesToBuild = maxLineagesToBuild;
    }
}