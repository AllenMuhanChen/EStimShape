package org.xper.allen.newga;

import org.xper.Dependency;
import org.xper.allen.ga.Child;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.function.BiConsumer;

public class RegimeSelectionProcess {

    @Dependency
    LineageDistributer distributer;

    public List<Child> select(String gaName){
        List<Child> newChildren = new LinkedList<>();

        //gather all lineages for this GA

        //distribute trials between lineages
        Map<Lineage, Integer> numTrialsForLineages = new HashMap<>();
        numTrialsForLineages = distributer.distribute(gaName);


        //evolve each lineage
        numTrialsForLineages.forEach(new BiConsumer<Lineage, Integer>() {
            @Override
            public void accept(Lineage lineage, Integer numTrials) {
                newChildren.addAll(lineage.evolve(numTrials));
            }
        });

        return newChildren;
    }

    public LineageDistributer getDistributer() {
        return distributer;
    }

    public void setDistributer(LineageDistributer distributer) {
        this.distributer = distributer;
    }
}