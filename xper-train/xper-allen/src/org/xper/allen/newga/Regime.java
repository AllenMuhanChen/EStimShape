package org.xper.allen.newga;

import org.xper.Dependency;
import org.xper.allen.ga.Child;

import java.util.List;

public class Regime {

    @Dependency
    ParentSelectionStrategy parentSelectionStrategy;

    @Dependency
    MorphingStrategy morphingStrategy;

    @Dependency
    TransitionStrategy transitionStrategy;

    public List<Child> select(long lineageId, int numTrials){
        List<Long> newChildrenIds = parentSelectionStrategy.selectParents(lineageId, numTrials);
        List<Child> newChildren = morphingStrategy.chooseMorphs(newChildrenIds);
        return newChildren;

    }

    public boolean shouldTransition(long lineageId){
        return transitionStrategy.shouldTransition(lineageId);
    }

    public ParentSelectionStrategy getParentSelectionStrategy() {
        return parentSelectionStrategy;
    }

    public void setParentSelectionStrategy(ParentSelectionStrategy parentSelectionStrategy) {
        this.parentSelectionStrategy = parentSelectionStrategy;
    }

    public MorphingStrategy getMorphingStrategy() {
        return morphingStrategy;
    }

    public void setMorphingStrategy(MorphingStrategy morphingStrategy) {
        this.morphingStrategy = morphingStrategy;
    }

    public TransitionStrategy getTransitionStrategy() {
        return transitionStrategy;
    }

    public void setTransitionStrategy(TransitionStrategy transitionStrategy) {
        this.transitionStrategy = transitionStrategy;
    }
}