package org.xper.intan;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.xper.Dependency;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedList;
import java.util.List;

public class UpcomingTasksFileNamingStrategy extends TaskIdFileNamingStrategy{

    @Dependency
    DataSource dataSource;

    @Dependency
    int numSlides;

    @Override
    protected String nameBaseFile(Long taskId) {
        int numUpcomingTasks = numSlides;

        List<Long> upcomingTaskIds = getUpcomingTaskIds(numUpcomingTasks, taskId);

        StringBuilder upcomingTaskIdsString = new StringBuilder();
        for (Long upcomingTaskId : upcomingTaskIds) {
            upcomingTaskIdsString.append(upcomingTaskId.toString()).append("_");
        }

        return upcomingTaskIdsString.toString();
    }


    private List<Long> getUpcomingTaskIds(int numUpcomingTasks, long firstTaskId) {
        final LinkedList<Long> taskIds = new LinkedList<Long>();
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.query(
                "SELECT task_id FROM TaskToDo WHERE task_id >= ? ORDER BY task_id LIMIT ?",
                new Object[] { firstTaskId, numUpcomingTasks },
                new RowCallbackHandler() {
                    @Override
                    public void processRow(ResultSet rs) throws SQLException {
                        taskIds.add(rs.getLong("task_id"));
                    }
                }
        );

        return taskIds;
    }

    public DataSource getDataSource() {
        return dataSource;
    }

    public void setDataSource(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    public int getNumSlides() {
        return numSlides;
    }

    public void setNumTasks(int numSlides) {
        this.numSlides = numSlides;
    }
}