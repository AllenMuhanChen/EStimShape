package org.xper.allen.ga;

import java.util.List;

public interface ParentSelector {

    /**
     * @param gaName
     * @return list of stimIds for the selected parents
     */
    public List<Long> selectParents(String gaName);
}
