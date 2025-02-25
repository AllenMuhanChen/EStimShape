package org.xper.experiment;

import org.xper.Dependency;
import org.xper.db.vo.SystemVariable;
import org.xper.experiment.DatabaseSystemVariableContainer;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.util.DbUtil;

import java.util.Map;
import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;
import javax.sql.DataSource;

/**
 * Logs system variables to the database.
 * We routinely clear / modify systemVars throughout training / experiments, this gives a paper trail
 * to track what parameters were used at varying time points in the experiment.
 */
public class SystemVarLogger implements ExperimentEventListener {

    @Dependency
    DataSource dataSource;

    @Dependency
    DatabaseSystemVariableContainer systemVarContainer;

    public SystemVarLogger() {
    }


    @Override
    public void experimentStart(long timestamp) {
        systemVarContainer.refresh();
        createSystemVarLogTableIfNotExists();
        logSystemVariables(timestamp);
    }

    private void createSystemVarLogTableIfNotExists() {
        System.out.println("SystemVarLog table does not exist. Creating...");
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.execute(
                "CREATE TABLE IF NOT EXISTS SystemVarLog (" +
                        "name VARCHAR(255) NOT NULL, " +
                        "arr_ind INT NOT NULL, " +
                        "tstamp BIGINT NOT NULL, " +
                        "val TEXT, " +
                        "PRIMARY KEY (name, arr_ind, tstamp)" +
                        ")"
        );
    }

    private void logSystemVariables(long timestamp) {
        // Get all system variables
        Map<String, SystemVariable> systemVars = systemVarContainer.vars;

        JdbcTemplate jt = new JdbcTemplate(dataSource);

        // Iterate through each system variable and write to database
        for (Map.Entry<String, SystemVariable> entry : systemVars.entrySet()) {
            String name = entry.getKey();
            SystemVariable sysVar = entry.getValue();
            List<String> values = sysVar.getValues();

            // Insert each value with its array index
            for (int i = 0; i < values.size(); i++) {
                jt.update(
                        "INSERT INTO SystemVarLog (name, arr_ind, tstamp, val) VALUES (?, ?, ?, ?)",
                        new Object[] { name, i, timestamp, values.get(i) }
                );
            }
        }
    }

    @Override
    public void experimentStop(long timestamp) {

    }


    public void setDataSource(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    public void setSystemVarContainer(DatabaseSystemVariableContainer systemVarContainer) {
        this.systemVarContainer = systemVarContainer;
    }
}