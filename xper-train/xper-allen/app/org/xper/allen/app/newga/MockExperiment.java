package org.xper.allen.app.newga;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.experiment.ExperimentRunner;
import org.xper.util.FileUtil;

public class MockExperiment {
    public static void main(String[] args) {
        FileUtil.loadTestSystemProperties("/xper.properties.pga.mock");
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));

//        MultiGaDbUtil dbUtil = context.getBean(MultiGaDbUtil.class);
//        JdbcTemplate jt = new JdbcTemplate(dbUtil.getDataSource());
//        jt.execute("TRUNCATE TABLE TaskToDo");
//        jt.execute("TRUNCATE TABLE TaskDone");
//        jt.execute("TRUNCATE TABLE StimSpec");
//        jt.execute("TRUNCATE TABLE BehMsg");
//        jt.execute("TRUNCATE TABLE BehMsgEye");
//        jt.execute("TRUNCATE TABLE StimObjData");
//        jt.execute("TRUNCATE TABLE ExpLog");
//        jt.execute("TRUNCATE TABLE AcqData");
//        jt.execute("TRUNCATE TABLE StimGaInfo");
//        jt.execute("TRUNCATE TABLE LineageGaInfo");


//        dbUtil.writeReadyGAandGenerationInfo("New3D");


        ExperimentRunner runner = context.getBean(ExperimentRunner.class);
        runner.run();
    }
}