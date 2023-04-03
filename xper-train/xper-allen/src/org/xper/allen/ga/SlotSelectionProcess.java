package org.xper.allen.ga;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.xper.Dependency;
import org.xper.allen.ga.regimescore.Regime;
import org.xper.allen.ga.regimescore.RegimeScoreSource;
import org.xper.allen.util.MultiGaDbUtil;

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
    Map<Regime, UnivariateRealFunction> slotFunctionForRegimes;

    /**
     * Once slots are assigned to lineages and regimes, this function maps the response rate of a parent
     * to likelihood that the parent should be selected based on the regime.
     */
    @Dependency
    Map<Regime, UnivariateRealFunction> fitnessFunctionForRegimes;

    @Dependency
    SpikeRateSource spikeRateSource;

    @Dependency
    MaxResponseSource maxResponseSource;

    public List<Child> select(String gaName) {
        List<Child> selectedParents = new LinkedList<>();

        List<Long> lineageIds = fetchLineageIds(gaName);

        Map<Long, Double> regimeScoreForLineages =
                calculateRegimeScoresForLineages(lineageIds);

        Map<Long, List<Slot>> slotsForLineages =
                createSlotsForLineages(regimeScoreForLineages);

        assignRegimesToSlotsForEachLineage(slotsForLineages, regimeScoreForLineages);

        // For Each slot, use the lineage to choose parents, and use the regime to assign fitness score
        fillSlotsWithParents(gaName, selectedParents, slotsForLineages);
        return selectedParents;
    }

    private List<Long> fetchLineageIds(String gaName) {
        return dbUtil.readAllLineageIds(gaName);
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
            regimeScoreForLineages.put(lineageId, regimeScoreSource.getLineageScore(lineageId));
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
                for (Slot slot : slots) {

                    // use lineageId to find potential parents
                    List<Long> potentialParents = dbUtil.readDoneStimIdsFromLineage(gaName, lineageId);

                    // find normalized normalizedResponses for each potential parents
                    List<Double> normalizedResponses = new LinkedList<>();
                    for (Long potentialParent : potentialParents) {
                        Double averageSpikeRate = spikeRateSource.getSpikeRate(potentialParent);
                        double normalizedSpikeRate = averageSpikeRate / maxResponseSource.getMaxResponse(gaName);
                        normalizedResponses.add(normalizedSpikeRate);
                    }

                    // use normalizedResponses to find fitness scores
                    List<Double> fitnessScores = new LinkedList<>();
                    for (Double response : normalizedResponses) {
                        fitnessScores.add(plugIntoFunction(fitnessFunctionForRegimes.get(slot.getRegime()), response));
                    }

                    // use fitnessFunctions and normalizedResponses to assign fitness scores to each potential parent
                    ProbabilityTable<Long> probabilitiesForParentIds = new ProbabilityTable<>(potentialParents, fitnessScores);

                    // select parents
                    selectedParents.add(new Child(probabilitiesForParentIds.sampleWithReplacement(), slot.getRegime()));
                }
            }
        });
    }

    private void assignRegimes(List<Slot> slotsForLineage, Double regimeScore) {
        Integer numSlotsForLineage = slotsForLineage.size();

        //calculate how many slotsForLineage to assign to each regime
        Map<Regime, Integer> numSlotsForRegimes = assignNumSlotsToRegimes(regimeScore, numSlotsForLineage);

        //populate slotsForLineage for regimes
        Iterator<Slot> slotsIterator = slotsForLineage.iterator();
        for (Regime regime : numSlotsForRegimes.keySet()) {
            int numSlotsAssigned = 0;
            while(numSlotsAssigned < numSlotsForRegimes.get(regime)) {
                slotsIterator.next().setRegime(regime);
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

    private Map<Regime, Integer> assignNumSlotsToRegimes(Double regimeScore, Integer numSlotsForLineage) {
        Map<Regime, Double> slotScoreForRegimes = calculateSlotScoresForRegimes(regimeScore);

        ProbabilityTable<Regime> probabilitiesForRegimes =
                new ProbabilityTable<>(slotScoreForRegimes);

        return drawSlotsForRegimes(probabilitiesForRegimes, numSlotsForLineage);
    }

    private Map<Regime, Double> calculateSlotScoresForRegimes(Double regimeScore) {
        Map<Regime, Double> slotScoreForRegimes = new LinkedHashMap<>();
        for (Regime regime : slotFunctionForRegimes.keySet()) {
            UnivariateRealFunction slotFunction = slotFunctionForRegimes.get(regime);
            Double slotScore = plugIntoFunction(slotFunction, regimeScore);
            slotScoreForRegimes.put(regime, slotScore);
        }
        return slotScoreForRegimes;
    }

    private Map<Regime, Integer> drawSlotsForRegimes(ProbabilityTable<Regime> probabilitiesForRegimes, Integer numSlotsForLineage) {
        Map<Regime, Integer> numSlotsForRegimes = new LinkedHashMap<>();
        for (int i = 0; i < numSlotsForLineage; i++) {
            Regime regime = probabilitiesForRegimes.sampleWithReplacement();
            numSlotsForRegimes.putIfAbsent(regime, 0);
            Integer numSlotsForRegime = numSlotsForRegimes.get(regime);
            numSlotsForRegimes.put(regime, numSlotsForRegime + 1);
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
        private Regime regime;

        public Slot(Long lineageId) {
            this.lineageId = lineageId;
        }

        public Long getLineageId() {
            return lineageId;
        }

        public void setLineageId(Long lineageId) {
            this.lineageId = lineageId;
        }

        public Regime getRegime() {
            return regime;
        }

        public void setRegime(Regime regime) {
            this.regime = regime;
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

    public Map<Regime, UnivariateRealFunction> getSlotFunctionForRegimes() {
        return slotFunctionForRegimes;
    }

    public void setSlotFunctionForRegimes(Map<Regime, UnivariateRealFunction> slotFunctionForRegimes) {
        this.slotFunctionForRegimes = slotFunctionForRegimes;
    }

    public Map<Regime, UnivariateRealFunction> getFitnessFunctionForRegimes() {
        return fitnessFunctionForRegimes;
    }

    public void setFitnessFunctionForRegimes(Map<Regime, UnivariateRealFunction> fitnessFunctionForRegimes) {
        this.fitnessFunctionForRegimes = fitnessFunctionForRegimes;
    }

    public SpikeRateSource getSpikeRateSource() {
        return spikeRateSource;
    }

    public void setSpikeRateSource(SpikeRateSource spikeRateSource) {
        this.spikeRateSource = spikeRateSource;
    }

    public MaxResponseSource getMaxResponseSource() {
        return maxResponseSource;
    }

    public void setMaxResponseSource(MaxResponseSource maxResponseSource) {
        this.maxResponseSource = maxResponseSource;
    }
}