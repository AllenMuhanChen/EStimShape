package org.xper.allen.intan.stimulation;

import java.util.ArrayList;
import java.util.List;

/**
 * Represents a split across multiple conditions, parsed from {value1;value2;...} syntax.
 * Each value can be a String, ParsedTuple, or ParsedList.
 */
public class ParsedSplit {
    private final List<Object> values;

    public ParsedSplit(List<Object> values) {
        this.values = new ArrayList<Object>(values);
    }

    public List<Object> getValues() {
        return values;
    }

    public Object get(int index) {
        return values.get(index);
    }

    public int size() {
        return values.size();
    }
}