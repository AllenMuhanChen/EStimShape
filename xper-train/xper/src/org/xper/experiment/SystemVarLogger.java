package org.xper.experiment;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.Dependency;
import org.xper.db.vo.SystemVariable;
import org.xper.experiment.listener.ExperimentEventListener;

import javax.sql.DataSource;
import java.util.List;
import java.util.Map;

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
    private long experimentStartTime;

    public SystemVarLogger() {
    }

    @Override
    public void experimentStart(long timestamp) {
        experimentStartTime = timestamp;
        systemVarContainer.refresh();
        createSystemVarLogTableIfNotExists();
        logSystemVariablesAtStart(experimentStartTime);
    }

    private void createSystemVarLogTableIfNotExists() {
        System.out.println("SystemVarLog table does not exist. Creating...");
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.execute(
                "CREATE TABLE IF NOT EXISTS SystemVarLog (" +
                        "name VARCHAR(255) NOT NULL, " +
                        "arr_ind INT NOT NULL, " +
                        "val TEXT, " +
                        "experiment_start_time BIGINT NOT NULL, " +
                        "experiment_stop_time BIGINT, " +
                        "PRIMARY KEY (name, arr_ind, experiment_start_time)" +
                        ")"
        );
    }

    private void logSystemVariablesAtStart(long timestamp) {
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
                        "INSERT INTO SystemVarLog (name, arr_ind, experiment_start_time, val) VALUES (?, ?, ?, ?)",
                        new Object[] { name, i, timestamp, values.get(i) }
                );
            }
        }
    }

    @Override
    public void experimentStop(long timestamp) {
        updateSystemVariablesWithStopTime(timestamp);
    }

    private void updateSystemVariablesWithStopTime(long timestamp) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);

        // Update the stop_time for all rows that have NULL in that column
        jt.update(
                "UPDATE SystemVarLog SET experiment_stop_time = ? WHERE experiment_stop_time IS NULL AND experiment_start_time = ?",
                new Object[]{timestamp, experimentStartTime}
        );
    }

    public void setDataSource(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    public void setSystemVarContainer(DatabaseSystemVariableContainer systemVarContainer) {
        this.systemVarContainer = systemVarContainer;
    }
}