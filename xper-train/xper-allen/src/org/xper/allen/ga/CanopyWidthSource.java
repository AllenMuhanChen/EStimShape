package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.LinkedList;
import java.util.List;
import java.util.function.Consumer;

public class CanopyWidthSource {

    @Dependency
    public static double THRESHOLD_PERCENTAGE = 0.8;

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    MaxResponseSource maxResponseSource;

    @Dependency
    SpikeRateSource spikeRateSource;
    private String gaName;
    private Double maxResponse;

    /**
     * Finds the canopy width associated with the lineage tree for any particular stimulus.
     *
     * @param stimId
     * @return
     */
    public Integer getCanopyWidth(Long stimId) {
        StimGaInfo gaInfo =  dbUtil.readStimGaInfo(stimId);
        gaName = gaInfo.getGaName();
        maxResponse = maxResponseSource.getMaxResponse(gaName);
        String treeSpec = gaInfo.getTreeSpec();
        Branch<Long> tree = Branch.fromXml(treeSpec);

        List<Long> canopyStims = findCanopy(tree);

        return canopyStims.size();
    }

    private List<Long> findCanopy(Branch<Long> tree) {
        //Finding the average spike rate for each stimulus and adding it to the list of canopy sitmuli
        // if it is above the threshold
        List<Long> canopyStims = new LinkedList<>();
        tree.forEach(new Consumer<Branch<Long>>() {
            @Override
            public void accept(Branch<Long> branch) {
                double spikeRate = getAverageSpikeRateForStim(branch.getIdentifier());
                if (spikeRate > THRESHOLD_PERCENTAGE * maxResponse) {
                    canopyStims.add(branch.getIdentifier());
                }
            }
        });
        return canopyStims;
    }

    private Double getAverageSpikeRateForStim(Long stimId) {
        return spikeRateSource.getSpikeRate(stimId);
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public MaxResponseSource getMaxResponseSource() {
        return maxResponseSource;
    }

    public void setMaxResponseSource(MaxResponseSource maxResponseSource) {
        this.maxResponseSource = maxResponseSource;
    }

    public SpikeRateSource getSpikeRateSource() {
        return spikeRateSource;
    }

    public void setSpikeRateSource(SpikeRateSource spikeRateSource) {
        this.spikeRateSource = spikeRateSource;
    }

    public static double getThresholdPercentage() {
        return THRESHOLD_PERCENTAGE;
    }

    public static void setThresholdPercentage(double thresholdPercentage) {
        THRESHOLD_PERCENTAGE = thresholdPercentage;
    }
}