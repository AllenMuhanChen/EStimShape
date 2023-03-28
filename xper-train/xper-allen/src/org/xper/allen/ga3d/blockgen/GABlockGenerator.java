package org.xper.allen.ga3d.blockgen;

import org.xper.Dependency;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.util.MultiGaDbUtil;

public abstract class GABlockGenerator extends AbstractMStickPngTrialGenerator {
    public static String GA_NAME;

    @Dependency
    MultiGaDbUtil dbUtil;

    @Override
    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public String getGaBaseName() {
        return GA_NAME;
    }

    public void setGaBaseName(String gaBaseName) {
        GA_NAME = gaBaseName;
    }
}