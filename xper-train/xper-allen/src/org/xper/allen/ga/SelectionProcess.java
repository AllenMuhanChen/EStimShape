package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.ArrayList;
import java.util.List;

public class SelectionProcess{

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    SpikeRateSource spikeRateSource;

    @Dependency
    CanopyWidthSource canopyWidthSource;

    @Dependency
    FitnessScoreCalculator fitnessScoreCalculator;

    public ProbabilityTable<Child> select(String gaName) {
        List<Long> allStimIds = dbUtil.readAllStimIdsForGa(gaName);
        List<Child> children = convertToChildren(allStimIds);
        List<Double> fitnesses = calculateFitnesses(children);
        ProbabilityTable<Child> table = new ProbabilityTable<>(children, fitnesses);
        return table;
    }

    private List<Child> convertToChildren(List<Long> allStimIds) {
        List<Child> children = new ArrayList<>();
        for (Long stimId : allStimIds) {
            children.add(new Child(stimId, Child.MorphType.GROWING));
            children.add(new Child(stimId, Child.MorphType.PRUNING));
        }

        return children;
    }

    private List<Double> calculateFitnesses(List<Child> children) {
        List<Double> fitnesses = new ArrayList<>();
        for (Child child : children) {
            Double averageSpikeRate = getAverageSpikeRate(child);
            Integer treeCanopyWidth = canopyWidthSource.getCanopyWidth(child.getStimId());

            Double fitnessScore = calculateFitnessScore(new FitnessScoreParameters(averageSpikeRate, treeCanopyWidth));
            fitnesses.add(fitnessScore);
        }


        return fitnesses;
    }

    private Double getAverageSpikeRate(Child child) {
        List<Double> spikeRates = spikeRateSource.getSpikeRates(child.getStimId());
        return average(spikeRates);
    }

    private double average(List<Double> spikeRates) {
        double averageSpikeRate = 0;
        for (Double spikeRate : spikeRates) {
            averageSpikeRate += spikeRate;
        }
        averageSpikeRate /= spikeRates.size();
        return averageSpikeRate;
    }

    private Double calculateFitnessScore(FitnessScoreParameters fitnessScoreParameters) {
        return fitnessScoreCalculator.calculateFitnessScore(fitnessScoreParameters);
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
}