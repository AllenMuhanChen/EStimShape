package org.xper.allen.intan;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.intan.TaskIdFileNamingStrategy;

public class GAInfoFileNamingStrategy extends TaskIdFileNamingStrategy {

    @Dependency
    String gaName;

    @Dependency
    MultiGaDbUtil dbUtil;

    @Override
    protected String nameBaseFile(Long experimentStartTStamp) {
        String experimentId = dbUtil.readCurrentExperimentId(gaName).toString();
        String genId = dbUtil.readMultiGAReadyGenerationInfo().getGenIdForGA(gaName).toString();
        return experimentId + "_" + genId + "_" + experimentStartTStamp.toString();
    }


    public String getGaName() {
        return gaName;
    }

    public void setGaName(String gaName) {
        this.gaName = gaName;
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }
}