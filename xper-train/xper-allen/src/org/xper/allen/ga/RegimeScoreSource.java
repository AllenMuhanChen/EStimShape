package org.xper.allen.ga;

import org.apache.commons.math.random.EmpiricalDistribution;
import org.apache.commons.math3.analysis.BivariateFunction;
import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;
import org.apache.commons.math3.distribution.MultivariateNormalDistribution;


public class RegimeScoreSource {

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    MaxResponseSource lineageMaxResponseSource;

    BivariateFunction  childParentResponseFunction;

    EmpiricalDistribution childParentResponseDistribution;

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