package org.xper.allen.app.nafc;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.Console;
import org.xper.allen.app.Experiment;
import org.xper.allen.nafc.blockgen.MStickPngBlockGen;
import org.xper.allen.util.AllenDbUtil;
import org.xper.util.FileUtil;

public class MStickPngNAFCTest {
    private final String[] emptyArgs = {""};
    private JavaConfigApplicationContext context;
    private AllenDbUtil dbUtil;

    @Before
    public void setUp() throws Exception {

        FileUtil.loadTestSystemProperties("/xper.properties.nafc");
        context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));
        dbUtil = context.getBean(AllenDbUtil.class);
    }

    @Test
    public void gen_trials(){
        prepDb();

        MStickPngBlockGen generator = context.getBean(MStickPngBlockGen.class);
        int numTrials = 10;
        Integer[] numDistractorsTypes = {1};
        double[] numDistractorsFrequencies = {1.0};
        double sampleScaleUpperLim = 10.0;
        double sampleRadiusLowerLim = 0.0;
        double sampleRadiusUpperLim = 0.0;
        double eyeWinsize = 10.0;
        double choiceRadiusLowerLim = 10.0;
        double choiceRadiusUpperLim = 10.0;
        double distractorDistanceLowerLim = 0.0;
        double distractorDistanceUpperLim = 0.0;
        double distractorScaleUpperLim = 0.0;
        int numMMCategories = 2;
        Integer[] numQMDistractorsTypes = {0};
        double[] numQMDistractorsFrequencies = {1.0};
        Integer[] numQMCategoriesTypes = {1};
        double[] numQMCategoriesFrequencies = {1.0};

        generator.generate(
                numTrials,
                numDistractorsTypes,
                numDistractorsFrequencies,
                sampleScaleUpperLim,
                sampleRadiusLowerLim,
                sampleRadiusUpperLim,
                eyeWinsize,
                choiceRadiusLowerLim,
                choiceRadiusUpperLim,
                distractorDistanceLowerLim,
                distractorDistanceUpperLim,
                distractorScaleUpperLim,
                numMMCategories,
                numQMDistractorsTypes,
                numQMDistractorsFrequencies,
                numQMCategoriesTypes,
                numQMCategoriesFrequencies
        );
    }

    @Test
    public void startExperiment(){
        Console.main(emptyArgs);
        Experiment.main(emptyArgs);
    }

    @Ignore
    @Test
    public void purgeDb(){
        prepDb();
    }


    private void prepDb() {
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
    }
}