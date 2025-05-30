package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;

public abstract class StimPropertyManager<T> {

    protected final JdbcTemplate jdbcTemplate;

    public StimPropertyManager(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
        createTableIfNotExists();
    }
    public abstract void createTableIfNotExists();
    public abstract void writeProperty(Long stimId, T property);
    public abstract T readProperty(Long stimId);
    public abstract String getTableName();
}