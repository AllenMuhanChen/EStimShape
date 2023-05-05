package org.xper.allen.ga;

import java.util.List;
import java.util.Map;

/**
 * Analyzes data for parents and selects parents for the next generation.
 */
public interface ParentAnalysisStrategy {
    public  List<Long> selectParents(Map<Long, ? extends ParentData> dataForParents);
}
