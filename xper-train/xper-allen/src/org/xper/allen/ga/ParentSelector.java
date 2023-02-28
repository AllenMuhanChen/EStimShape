package org.xper.allen.ga;

import java.util.List;

public interface ParentSelector {

    public List<Long> selectParents(String gaName);
}
