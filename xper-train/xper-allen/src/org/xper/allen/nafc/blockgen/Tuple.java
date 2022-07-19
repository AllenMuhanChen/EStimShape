package org.xper.allen.nafc.blockgen;

public class Tuple<Type> {

    Type first;
    Type second;


    public Tuple(Type first, Type second) {
        this.first = first;
        this.second = second;
    }

    public Tuple(){};

    public Type getFirst() {
        return first;
    }

    public void setFirst(Type first) {
        this.first = first;
    }

    public Type getSecond() {
        return second;
    }

    public void setSecond(Type second) {
        this.second = second;
    }
}
