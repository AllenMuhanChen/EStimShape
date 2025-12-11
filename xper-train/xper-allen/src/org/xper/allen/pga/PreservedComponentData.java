package org.xper.allen.pga;

import java.util.List;

public class PreservedComponentData {
    private final List<Integer> compsToPreserve;  // components to preserve for next generation
    private final Long parentId;
    private final List<Integer> parentCompsPreserved;  // components preserved from parent to create this

    public PreservedComponentData(List<Integer> compsToPreserve, Long parentId, List<Integer> parentCompsPreserved) {
        this.compsToPreserve = compsToPreserve;
        this.parentId = parentId;
        this.parentCompsPreserved = parentCompsPreserved;
    }

    public List<Integer> getCompsToPreserve() {
        return compsToPreserve;
    }

    public Long getParentId() {
        return parentId;
    }

    public List<Integer> getParentCompsPreserved() {
        return parentCompsPreserved;
    }
}