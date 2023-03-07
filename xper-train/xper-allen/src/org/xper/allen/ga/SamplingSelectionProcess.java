package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;

public class SamplingSelectionProcess {

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    SpikeRateSource spikeRateSource;

    @Dependency
    CanopyWidthSource canopyWidthSource;

    @Dependency
    FitnessScoreCalculator<TreeFitnessScoreParameters> fitnessScoreCalculator;

    @Dependency
    Integer numChildrenToSelect;

    private ProbabilityTable<Child> table;
    private String gaName;

    /**
     * Selects children from the database based on their fitness scores.
     * The fitness scores are calculated based on the spike rates and canopy widths of the children.
     *
     * @param gaName String of the name of the GA to select children from
     * @return a list of children that were selected
     */
    public List<Child> select(String gaName) {
        this.gaName = gaName;
        List<Long> allStimIds = dbUtil.readAllStimIdsForGa(gaName);
        List<Child> possibleChildren = convertToChildren(allStimIds);
        List<Double> fitnesses = calculateFitnesses(possibleChildren);

        return selectChildren(possibleChildren, fitnesses);
    }

    /**
     * Selects children from the list of possible children based on their fitness scores.
     * The fitness scores are used to create a probability table, and then children are
     * sampled from the table with replacement.
     */
    private List<Child> selectChildren(List<Child> possibleChildren, List<Double> fitnesses) {
        List<Child> selectedChildren = new LinkedList<>();
        table = new ProbabilityTable<>(possibleChildren, fitnesses);
        for (int i = 0; i < numChildrenToSelect; i++) {
            Child child = table.sampleWithReplacement();
            selectedChildren.add(child);
        }
        return selectedChildren;
    }

    /**
     * Converts a list of stimIds into a list of possible children that could be selected
     * in the selection process.
     * @param stimIds
     */
    private List<Child> convertToChildren(List<Long> stimIds) {
        List<Child> children = new ArrayList<>();
        for (Long stimId : stimIds) {
            children.add(new Child(stimId, Regime.ONE));
            children.add(new Child(stimId, Regime.TWO));
        }

        return children;
    }

    private List<Double> calculateFitnesses(List<Child> children) {
        List<Double> fitnesses = new ArrayList<>();
        for (Child child : children) {
            Double averageSpikeRate = getAverageSpikeRate(child);
            Integer treeCanopyWidth = getTreeCanopyWidth(child);

            Double fitnessScore = calculateFitnessScore(new TreeFitnessScoreParameters(averageSpikeRate, treeCanopyWidth, gaName));
            fitnesses.add(fitnessScore);
        }
        return fitnesses;
    }

    private Double getAverageSpikeRate(Child child) {
        List<Double> spikeRates = spikeRateSource.getSpikeRates(child.getStimId());
        return average(spikeRates);
    }

    private Integer getTreeCanopyWidth(Child child) {
        return canopyWidthSource.getCanopyWidth(child.getStimId());
    }

    private Double calculateFitnessScore(TreeFitnessScoreParameters fitnessScoreParameters) {
        return fitnessScoreCalculator.calculateFitnessScore(fitnessScoreParameters);
    }

    private double average(List<Double> spikeRates) {
        double averageSpikeRate = 0;
        for (Double spikeRate : spikeRates) {
            averageSpikeRate += spikeRate;
        }
        averageSpikeRate /= spikeRates.size();
        return averageSpikeRate;
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public SpikeRateSource getSpikeRateSource() {
        return spikeRateSource;
    }

    public void setSpikeRateSource(SpikeRateSource spikeRateSource) {
        this.spikeRateSource = spikeRateSource;
    }

    public CanopyWidthSource getCanopyWidthSource() {
        return canopyWidthSource;
    }

    public void setCanopyWidthSource(CanopyWidthSource canopyWidthSource) {
        this.canopyWidthSource = canopyWidthSource;
    }

    public FitnessScoreCalculator getFitnessScoreCalculator() {
        return fitnessScoreCalculator;
    }

    public void setFitnessScoreCalculator(FitnessScoreCalculator fitnessScoreCalculator) {
        this.fitnessScoreCalculator = fitnessScoreCalculator;
    }

    public ProbabilityTable<Child> getTable() {
        return table;
    }

    public Integer getNumChildrenToSelect() {
        return numChildrenToSelect;
    }

    public void setNumChildrenToSelect(Integer numChildrenToSelect) {
        this.numChildrenToSelect = numChildrenToSelect;
    }
}