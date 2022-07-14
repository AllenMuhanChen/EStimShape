package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.nafc.blockgen.NAFC;

import java.util.LinkedList;
import java.util.List;

public class Rand<Type> extends NAFC<Type>{
    private List<Type> qualitativeMorphDistractors = new LinkedList<>();
    private List<Type> randDistractors = new LinkedList<>();

    public Rand(Type sample, Type match, List<Type> distractors, List<Type> qualitativeMorphDistractors, List<Type> randDistractors) {
        super(sample, match, distractors);
        this.qualitativeMorphDistractors = qualitativeMorphDistractors;
        this.randDistractors = randDistractors;
    }

    public Rand() {

    }

    public void addQualitativeMorphDistractor(Type qmDistractor){
        qualitativeMorphDistractors.add(qmDistractor);
        addToAllDistractors(qmDistractor);
    }

    public void addRandDistractor(Type randDistractor){
        randDistractors.add(randDistractor);
        addToAllDistractors(randDistractor);
    }

    public List<Type> getQualitativeMorphDistractors() {
        return qualitativeMorphDistractors;
    }

    public void setQualitativeMorphDistractors(List<Type> qualitativeMorphDistractors) {
        this.qualitativeMorphDistractors = qualitativeMorphDistractors;
    }

    public List<Type> getRandDistractors() {
        return randDistractors;
    }

    public void setRandDistractors(List<Type> randDistractors) {
        this.randDistractors = randDistractors;
    }
}
