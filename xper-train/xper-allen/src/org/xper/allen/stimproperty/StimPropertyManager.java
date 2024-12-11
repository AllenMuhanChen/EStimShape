package org.xper.allen.stimproperty;


public interface StimPropertyManager<T> {
    void createTableIfNotExists();
    void writeProperty(Long stimId);
    T readProperty(Long stimId);
    String getTableName();
}