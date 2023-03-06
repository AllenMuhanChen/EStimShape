package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;

public class RegimeScoreSource {

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    MaxResponseSource lineageMaxResponseSource;


    public Double getRegimeScore(Long founderId) {
        //
        return null;
    }



    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }
}