package org.xper.allen.newga;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.ga.Child;
import org.xper.allen.ga.regimescore.MutationType;

import java.util.LinkedList;
import java.util.List;

import static org.junit.Assert.*;

public class RegimeTest {

    @Before
    public void setUp() throws Exception {
    }

    @Test
    public void regimeZero(){
        ParentSelectionStrategy parentSelectionStrategy = new ParentSelectionStrategy() {
            @Override
            public List<Long> selectParents(long lineageId, int numTrials) {
                LinkedList<Long> parents = new LinkedList<>();
                for (int i=0; i<numTrials; i++){
                    parents.add(0L);
                }
                return parents;
            }
        };

        MorphingStrategy morphingStrategy = new MorphingStrategy() {
            @Override
            public List<Child> chooseMorphs(List<Long> newChildrenIds) {
                LinkedList<Child> child = new LinkedList<>();
                for (Long parentId : newChildrenIds){
                    child.add(new Child(0, MutationType.ZERO,1.0));
                }
                return child;
            }
        };

        TransitionStrategy transitionStrategy = new TransitionStrategy() {
            @Override
            public boolean shouldTransition(long lineageId) {
                // top stimulus is past certain threshold
                return false;
            }
        };

    }
}