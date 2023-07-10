package org.xper.allen.newga;

import org.xper.allen.ga.Child;

import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;

public class Lineage {

    private final long lineageId;
    private final Iterator<Regime> regimes;

    private Regime currentRegime;

    public Lineage(long lineageId, List<Regime> regimes) {
        this.lineageId = lineageId;
        this.regimes = regimes.iterator();
        this.currentRegime = this.regimes.next();
    }

    public List<Child> evolve(int numTrials){
        if (regimes.hasNext()) {
            List<Child> newChildren = currentRegime.select(lineageId, numTrials);

            if (currentRegime.shouldTransition(lineageId)) {
                currentRegime = regimes.next();
            }

            return newChildren;
        }
        else{
            return new LinkedList<>();
        }

    }
}