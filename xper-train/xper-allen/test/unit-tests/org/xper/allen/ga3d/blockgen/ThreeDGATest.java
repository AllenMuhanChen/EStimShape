package org.xper.allen.ga3d.blockgen;

import com.sun.org.apache.xpath.internal.operations.Mult;
import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.ga.MockParentSelector;
import org.xper.allen.ga.ParentSelector;
import org.xper.allen.util.DbUtilFactory;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.db.vo.GenerationTaskToDoList;
import org.xper.db.vo.TaskToDoEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

import java.util.LinkedList;
import java.util.List;

import static org.junit.Assert.*;

public class ThreeDGATest {
    GA3DBlockGen generator = new GA3DBlockGen();
    private Long testParentId;

    @Before
    public void setUp(){
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));
        generator = context.getBean(GA3DBlockGen.class);

        JdbcTemplate jt = new JdbcTemplate(generator.getDbUtil().getDataSource());
        jt.execute("TRUNCATE TABLE TaskToDo");
        jt.execute("TRUNCATE TABLE TaskDone");

        generator.setParentSelector(new MockParentSelector(context.getBean(MultiGaDbUtil.class)));
        generator.setUp(1, 20, 5, new Coordinates2D(0,0), generator.channels);
    }

    @Test
    public void write() {
        List<String> gaNames = new LinkedList<>();
        gaNames.add("3D-1");
        generator.getDbUtil().writeReadyGAsAndGenerationsInfo(gaNames);
        generator.generate(); //first gen

        //MOCK DO FIRST GENERATION
        GenerationTaskToDoList list = generator.getDbUtil().readTaskToDoByGaAndGeneration("3D-1", 1);
        List<TaskToDoEntry> taskList = list.getTasks();
        for (TaskToDoEntry taskToDo:taskList){
            generator.getDbUtil().writeTaskDone(generator.getGlobalTimeUtil().currentTimeMicros(), taskToDo.getTaskId(), 0, "3D-1", 1);
        }

        ThreadUtil.sleep(1000);

        generator.generate(); //second gen
        List<Long> stimsToMorph = generator.stimsToMorph;


        assertMakesNewTrial();

    }

    private void assertMakesNewTrial() {
        fail();
    }


    private ParentSelector testParentSelector() {
        return new ParentSelector() {
            @Override
            public List<Long> selectParents(List<String> channels, String gaName) {
                LinkedList<Long> testList = new LinkedList<Long>();
                testList.add(testParentId);
                return testList;
            }
        };
    }
}