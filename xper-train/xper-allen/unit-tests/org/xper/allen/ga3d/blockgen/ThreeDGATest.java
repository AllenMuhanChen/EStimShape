package org.xper.allen.ga3d.blockgen;

import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.config.MStickPngConfig;
import org.xper.allen.config.ThreeDGAConfig;
import org.xper.allen.ga.ParentSelector;
import org.xper.allen.util.DbUtilFactory;
import org.xper.drawing.Coordinates2D;
import org.xper.util.FileUtil;

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
        generator.setDbUtil(DbUtilFactory.createGaDbUtil("allen_estimshape_dev_221110"));
        generator.setParentSelector(testParentSelector());
        generator.setUp(1, 2, 5, new Coordinates2D(0,0));
    }

    @Test
    public void write() {
        List<String> gaNames = new LinkedList<>();
        gaNames.add("3D-1");
        generator.getDbUtil().writeReadyGAsAndGenerationsInfo(gaNames);
        generator.generate(); //first gen
        testParentId = generator.getDbUtil().readTaskToDoMaxId();
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
            public List<Long> selectParents() {
                LinkedList<Long> testList = new LinkedList<Long>();
                testList.add(testParentId);
                return testList;
            }
        };
    }
}