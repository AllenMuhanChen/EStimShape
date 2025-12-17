package org.xper.allen.pga;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.stimproperty.StimPropertyManager;

public class PositionPropertyManager extends StimPropertyManager<MStickPosition> {
    public PositionPropertyManager(JdbcTemplate jdbcTemplate) {
        super(jdbcTemplate);
    }

    @Override
    public void createTableIfNotExists() {

    }

    @Override
    public void writeProperty(Long stimId, MStickPosition property) {

    }


    @Override
    public MStickPosition readProperty(Long stimId) {
        return null;
    }

    @Override
    public String getTableName() {
        return "";
    }
}
