package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;

public class CanopyWidthSource {

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    MaxResponseSource maxResponseSource;

    public Integer getCanopyWidth(Long stimId) {
        StimGaInfo gaInfo =  dbUtil.readStimGaInfo(stimId);
        String treeSpec = gaInfo.getTreeSpec();

        return 0;
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
}