package org.xper.app.rfplot;

import java.util.*;

public class CyclicIterator<T> implements Iterator<T> {
    int size;
    List<T> list = new LinkedList<>();
    int i=0;
    public CyclicIterator(Set<T> set) {
        list.addAll(set);
        size = set.size();
    }

    @Override
    public boolean hasNext() {
        return true;
    }

    @Override
    public T next() {
        return list.get(i++ % size);
    }

    public T previous() {
        return list.get(i-- % size);
    }

    public T first(){
        return list.get(0);
    }
}
