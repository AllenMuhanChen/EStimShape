package org.xper.allen.ga;

import java.util.List;
import java.util.Map;

public interface ParentSelectorStrategy {
    public  List<Long> selectParents(Map<Long, ? extends ParentData> dataForParents);
}
