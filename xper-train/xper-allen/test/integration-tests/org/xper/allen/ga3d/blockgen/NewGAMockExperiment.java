package org.xper.allen.ga3d.blockgen;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.GAConsole;
import org.xper.allen.app.GAExperiment;
import org.xper.allen.newga.blockgen.NewGABlockGenerator;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.app.acq.AcqServer;
import org.xper.util.FileUtil;

import java.util.List;
import java.util.Map;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class NewGAMockExperiment {
    private final String[] emptyArgs = {""};
    private NewGABlockGenerator generator;
    private MultiGaDbUtil dbUtil;
    private String gaBaseName;

    @Before
    public void setUp(){
        FileUtil.loadTestSystemProperties("/xper.properties.newga.mock");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));
        generator = context.getBean(NewGABlockGenerator.class);

        gaBaseName = generator.getGaBaseName();
        dbUtil = generator.getDbUtil();
    }

    @Test
    public void startExperiment(){
        prepDB();
        GAConsole.main(emptyArgs);
        GAExperiment.main(emptyArgs);
    }

    @Test
    public void writeFirstGeneration(){
        prepDB();

        generator.generate(); //first gen
        assertEquals(1, (long) dbUtil.readMultiGAReadyGenerationInfo().getGenIdForGA(gaBaseName));

        GAConsole.main(emptyArgs);
        GAExperiment.main(emptyArgs);

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
            assertTrue(taskIds.size() == generator.getNumTrialsPerStimulus());
        });
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

        dbUtil.writeReadyGAandGenerationInfo(gaBaseName);
    }
}