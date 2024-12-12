package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;

public abstract class StimPropertyManager<T> {

    protected final JdbcTemplate jdbcTemplate;

    public StimPropertyManager(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
        createTableIfNotExists();
    }
    abstract void createTableIfNotExists();
    abstract void writeProperty(Long stimId, T property);
    abstract T readProperty(Long stimId);
    abstract String getTableName();
}