package org.xper.rfplot.gui;

import java.util.*;

/**
 * @author Allen Chen
 */
public class CyclicIterator<T> implements Iterator<T> {
    int size;
    List<T> list = new LinkedList<>();
    int i=0;
    public CyclicIterator(Collection<T> col) {
        list.addAll(col);
        size = col.size();
        i=0;
    }

    @Override
    public boolean hasNext() {
        if (size>0) return true;
        else return false;
    }

    @Override
    public T next() {
        i++;
        return list.get(Math.floorMod(i, size));
    }

    public T previous() {
        i--;
        return list.get(Math.floorMod(i, size));
    }

    public T first(){
        i=0;
        return list.get(i);
    }

    public T get(int i){
        return list.get(i);
    }

    public int getPosition(){
        return i;
    }
}
