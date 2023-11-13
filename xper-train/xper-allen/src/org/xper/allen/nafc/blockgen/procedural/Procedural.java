package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.blockgen.NAFC;

import java.util.LinkedList;
import java.util.List;

public class Procedural<Type> extends NAFC<Type> {
    public List<Type> randDistractors = new LinkedList<>();
    public List<Type> proceduralDistractors = new LinkedList<>();

    public Procedural(Type sample, Type match, List<Type> proceduralDistractors, List<Type> randDistractors) {
        super(sample, match, new LinkedList<>());
        this.randDistractors = randDistractors;
        this.proceduralDistractors = proceduralDistractors;
        getAllDistractors().addAll(randDistractors);
        getAllDistractors().addAll(proceduralDistractors);
    }

    public void addProceduralDistractor(Type proceduralDistractor){
        proceduralDistractors.add(proceduralDistractor);
        addToAllDistractors(proceduralDistractor);
    }

    public void addRandDistractor(Type randDistractor){
        randDistractors.add(randDistractor);
        addToAllDistractors(randDistractor);
    }
}