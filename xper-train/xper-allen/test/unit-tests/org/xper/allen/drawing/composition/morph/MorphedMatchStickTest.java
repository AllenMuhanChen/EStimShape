package org.xper.allen.drawing.composition.morph;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;
import org.xper.alden.drawing.drawables.PNGmaker;
import org.xper.drawing.stick.MatchStick;
import org.xper.util.ResourceUtil;
import org.xper.util.ThreadUtil;

import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;

import static org.xper.drawing.TestDrawingWindow.initXperLibs;

public class MorphedMatchStickTest {

    private MorphedMatchStick parentMStick;
    private String testBin;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = ResourceUtil.getResource("testBin");

        parentMStick = new MorphedMatchStick();
        parentMStick.setProperties(30, "SHADE");
//        String test_stick_path = ResourceUtil.getResource("test-stick.xml");
//        parentMStick.genMatchStickFromFile(test_stick_path);
        parentMStick.genMatchStickRand();


        drawPng(parentMStick, 1L);
    }


    @Test
    @Ignore
    public void growingMatchStick() {
        GrowingMatchStick growingMatchStick = new GrowingMatchStick(1/3.0);
        growingMatchStick.setProperties(30.0, "SHADE");
        growingMatchStick.genGrowingMatchStick(parentMStick, 0.2);
        ThreadUtil.sleep(500);
        drawPng(growingMatchStick, 2L);
    }

    @Test
    @Ignore
    public void pruningMatchStick(){
        PruningMatchStick pruningMatchStick = new PruningMatchStick();
        pruningMatchStick.setProperties(30.0, "SHADE");
        pruningMatchStick.genPruningMatchStick(parentMStick, 0.6, 1);
        ThreadUtil.sleep(500);
        drawPng(pruningMatchStick, 2L);
    }

    @Test
    @Ignore
    public void removeLimbMatchStick(){
        MorphedMatchStick removeLimbMatchStick = new MorphedMatchStick();
        removeLimbMatchStick.setProperties(30.0, "SHADE");
        removeLimbMatchStick.genRemovedLimbsMatchStick(parentMStick, new HashSet<>(Arrays.asList(1)));
        ThreadUtil.sleep(500);
        drawPng(removeLimbMatchStick, 2L);
    }

    @Test
    @Ignore
    public void addLimbMatchStick(){
        MorphedMatchStick addLimbMatchStick = new MorphedMatchStick();
        addLimbMatchStick.setProperties(30.0, "SHADE");
        addLimbMatchStick.genAddedLimbsMatchStick(parentMStick, 1);
        ThreadUtil.sleep(500);
        drawPng(addLimbMatchStick, 2L);
    }

    @Test
    @Ignore
    public void mutate() {
        Map<Integer, ComponentMorphParameters> morphParams = new HashMap<>();
        morphParams.put(1, new NormalDistributedComponentMorphParameters(0.25, new NormalMorphDistributer(1/3.0)));
//        morphParams.put(2, new ComponentMorphParameters(0.2));


        MorphedMatchStick childMStick = new MorphedMatchStick();
        childMStick.setProperties(30.0, "SHADE");
        childMStick.genMorphedComponentsMatchStick(morphParams, parentMStick);
        ThreadUtil.sleep(500);
        drawPng(childMStick, 2L);

        System.out.println("Parents: ");
        System.out.println("Comp 1: ");
        System.out.println(parentMStick.getComp()[1].getRadInfo()[0][1]);
        System.out.println(parentMStick.getComp()[1].getRadInfo()[1][1]);
        System.out.println(parentMStick.getComp()[1].getRadInfo()[2][1]);
        System.out.println("Comp 2: ");
        System.out.println(parentMStick.getComp()[2].getRadInfo()[0][1]);
        System.out.println(parentMStick.getComp()[2].getRadInfo()[1][1]);
        System.out.println(parentMStick.getComp()[2].getRadInfo()[2][1]);
        System.out.println("Children: ");
        System.out.println("Comp 1: ");
        System.out.println(childMStick.getComp()[1].getRadInfo()[0][1]);
        System.out.println(childMStick.getComp()[1].getRadInfo()[1][1]);
        System.out.println(childMStick.getComp()[1].getRadInfo()[2][1]);
        System.out.println("Comp 2: ");
        System.out.println(childMStick.getComp()[2].getRadInfo()[0][1]);
        System.out.println(childMStick.getComp()[2].getRadInfo()[1][1]);
        System.out.println(childMStick.getComp()[2].getRadInfo()[2][1]);


        System.out.println("Done");
    }

    private void drawPng(MatchStick matchStick, long id) {
        PNGmaker pngMaker = new PNGmaker(500, 500);
        pngMaker.createAndSavePNGsfromObjs(Arrays.asList(matchStick), Arrays.asList(new Long[]{id}), testBin);
    }

}