package org.xper.allen.ga;

import java.util.List;

public interface ParentSelectorStrategy {
    public List<Long> analyze(List<Parent> stims);
}
