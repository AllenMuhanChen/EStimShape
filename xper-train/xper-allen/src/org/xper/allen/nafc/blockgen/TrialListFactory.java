package org.xper.allen.nafc.blockgen;

import org.xper.allen.Stim;

import java.util.List;

public interface TrialListFactory<T extends Stim> {
    List<T> createTrials();
}