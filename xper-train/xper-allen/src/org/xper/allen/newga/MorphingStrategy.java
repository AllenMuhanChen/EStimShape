package org.xper.allen.newga;

import org.xper.allen.ga.Child;

import java.util.List;

public interface MorphingStrategy {
    List<Child> chooseMorphs(List<Long> newChildrenIds);
}