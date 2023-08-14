package org.xper.allen.ga3d.blockgen;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.GAConsole;
import org.xper.allen.app.GAExperiment;
import org.xper.allen.ga.ParentSelector;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.util.FileUtil;

import java.util.LinkedList;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

public class ThreeDGAMockExperiment {
    public static final int NUM_TRIALS_PER_STIMULI = 2;
    private final String[] emptyArgs = {""};
    GA3DLineageBlockGenerator generator = new GA3DLineageBlockGenerator();
    private MultiGaDbUtil dbUtil;
    private Long testParentId;

    @Before
    public void setUp(){
        FileUtil.loadTestSystemProperties("/xper.properties.3dga.mock");

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));
        generator = context.getBean(GA3DLineageBlockGenerator.class);
        dbUtil = generator.getDbUtil();

        generator.setUp(20,5, new Coordinates2D(0,0), generator.channels);
    }

    @Test
    public void writeFirstGeneration(){
        prepDB();
        generator.generate(); //first gen

        assertEquals(1, (long) dbUtil.readMultiGAReadyGenerationInfo().getGenIdForGA("3D-1"));
        assertEquals(1, (long) dbUtil.readMultiGAReadyGenerationInfo().getGenIdForGA("3D-2"));

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
        jt.execute("TRUNCATE TABLE StimGaInfo");
        jt.execute("TRUNCATE TABLE LineageGaInfo");


        List<String> gaNames = new LinkedList<>();
        gaNames.add("3D-1");
        gaNames.add("3D-2");
        dbUtil.writeReadyGAsAndGenerationsInfo(gaNames);
    }

    @Test
    public void writeNextGeneration() {

        generator.generate(); //second gen

        assertCorrectNumberOfRepetitions();
//        GAConsole.main(emptyArgs);
//        GAExperiment.main(emptyArgs);
    }

    private void assertCorrectNumberOfRepetitions() {
        Map<Long, List<Long>> taskIdsForStimIds = generator.getDbUtil().readTaskDoneIdsForStimIds("3D-1", generator.getDbUtil().readTaskDoneMaxGenerationIdForGa("3D-1"));
        taskIdsForStimIds.forEach((stimId, taskIds) -> {
            assertTrue(taskIds.size() == NUM_TRIALS_PER_STIMULI);
        });
    }


    private void assertMakesNewTrial() {
        fail();
    }


    private ParentSelector testParentSelector() {
        return new ParentSelector() {
            @Override
            public List<Long> selectParents(String gaName) {
                LinkedList<Long> testList = new LinkedList<Long>();
                testList.add(testParentId);
                return testList;
            }
        };
    }
}