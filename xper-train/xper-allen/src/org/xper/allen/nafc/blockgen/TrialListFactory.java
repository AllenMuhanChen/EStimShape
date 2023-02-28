package org.xper.allen.nafc.blockgen;

import org.xper.allen.Stim;

import java.util.List;

public interface TrialListFactory {
    List<Stim> createTrials();
}
