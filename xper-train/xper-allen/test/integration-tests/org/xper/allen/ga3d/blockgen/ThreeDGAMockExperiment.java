package org.xper.allen.ga3d.blockgen;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.GAConsole;
import org.xper.allen.app.GAExperiment;
import org.xper.allen.ga.MockParentSelector;
import org.xper.allen.ga.ParentSelector;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.db.vo.GenerationTaskToDoList;
import org.xper.db.vo.TaskToDoEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

import java.util.LinkedList;
import java.util.List;

import static org.junit.Assert.*;

public class ThreeDGAMockExperiment {
    private final String[] emptyArgs = {""};
    GA3DBlockGen generator = new GA3DBlockGen();
    private MultiGaDbUtil dbUtil;
    private Long testParentId;

    @Before
    public void setUp(){
        FileUtil.loadTestSystemProperties("/xper.properties.3dga.mock");

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));
        generator = context.getBean(GA3DBlockGen.class);
        dbUtil = generator.getDbUtil();
        //TODO: mockparentselector should read our python generated responses
        generator.setParentSelector(new MockParentSelector(context.getBean(MultiGaDbUtil.class)));

        generator.setUp(1, 5, 5, new Coordinates2D(0,0), generator.channels);
    }

    @Test
    public void writeFirstGeneration(){
        prepDB();
        generator.generate(); //first gen

        assertEquals(1, (long) dbUtil.readMultiGAReadyGenerationInfo().getGenIdForGA("3D-1"));

        GAConsole.main(emptyArgs);
        GAExperiment.main(emptyArgs);
    }

    private void prepDB() {
        JdbcTemplate jt = new JdbcTemplate(dbUtil.getDataSource());
        jt.execute("TRUNCATE TABLE TaskToDo");
        jt.execute("TRUNCATE TABLE TaskDone");
        jt.execute("TRUNCATE TABLE StimSpec");
        jt.execute("TRUNCATE TABLE BehMsg");
        jt.execute("TRUNCATE TABLE BehMsgEye");
        jt.execute("TRUNCATE TABLE StimObjData");
        jt.execute("TRUNCATE TABLE ExpLog");
        jt.execute("TRUNCATE TABLE AcqData");


        List<String> gaNames = new LinkedList<>();
        gaNames.add("3D-1");
        dbUtil.writeReadyGAsAndGenerationsInfo(gaNames);
    }

    @Test
    public void write() {



        //MOCK DO FIRST GENERATION
        GenerationTaskToDoList list = dbUtil.readTaskToDoByGaAndGeneration("3D-1", 1);
        List<TaskToDoEntry> taskList = list.getTasks();
        for (TaskToDoEntry taskToDo:taskList){
            dbUtil.writeTaskDone(generator.getGlobalTimeUtil().currentTimeMicros(), taskToDo.getTaskId(), 0, "3D-1", 1);
        }

        ThreadUtil.sleep(1000);

        generator.generate(); //second gen
        List<Long> stimsToMorph = generator.stimsToMorph;


//        assertMakesNewTrial();

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