package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.nafc.blockgen.NAFC;

import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

public class Procedural<Type> extends NAFC<Type> {
    protected List<Type> randDistractors = new LinkedList<>();
    protected List<Type> proceduralDistractors = new LinkedList<>();

    public Procedural(Type sample, Type match, List<Type> proceduralDistractors, List<Type> randDistractors) {
        super(sample, match, new LinkedList<>());
        for (Type proceduralDistractor : proceduralDistractors) {
            addProceduralDistractor(proceduralDistractor);
        }
        for (Type randDistractor : randDistractors) {
            addRandDistractor(randDistractor);
        }
    }

    public Procedural() {
    }

    public void addProceduralDistractor(Type proceduralDistractor){
        proceduralDistractors.add(proceduralDistractor);
        addToAllDistractors(proceduralDistractor);
    }

    public void addRandDistractor(Type randDistractor){
        randDistractors.add(randDistractor);
        addToAllDistractors(randDistractor);
    }

    public List<Type> getRandDistractors() {
        return Collections.unmodifiableList(randDistractors);
    }

    public List<Type> getProceduralDistractors() {
        return Collections.unmodifiableList(proceduralDistractors);
    }


}