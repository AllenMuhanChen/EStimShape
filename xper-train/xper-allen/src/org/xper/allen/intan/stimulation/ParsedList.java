package org.xper.allen.intan.stimulation;

import java.util.ArrayList;
import java.util.List;

public class ParsedList {
    private final List<String> values;

    public ParsedList(List<String> values) {
        this.values = new ArrayList<String>(values);
    }

    public List<String> getValues() {
        return values;
    }

    public String get(int index) {
        return values.get(index);
    }

    public int size() {
        return values.size();
    }
}