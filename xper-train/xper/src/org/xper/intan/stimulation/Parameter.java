package org.xper.intan.stimulation;

public class Parameter<T> {
    private final String key;
    private final T value;

    public Parameter(String key, T value) {
        this.key = key;
        this.value = value;
    }

    public String getKey() {
        return key;
    }

    public T getValue() {
        return value;
    }
}