package org.xper.allen.drawing.composition;

import org.junit.Before;
import org.junit.Test;
import org.xper.alden.drawing.drawables.PNGmaker;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.drawing.stick.MatchStick;
import org.xper.util.ResourceUtil;
import org.xper.util.ThreadUtil;

import javax.media.j3d.Morph;
import java.util.Arrays;
import java.util.HashMap;
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
        parentMStick.setProperties(30);
//        String test_stick_path = ResourceUtil.getResource("test-stick.xml");
//        parentMStick.genMatchStickFromFile(test_stick_path);
        parentMStick.genMatchStickRand();


        drawPng(parentMStick, 1L);
    }

    @Test
    public void mutate() {
        Map<Integer, ComponentMorphParameters> morphParams = new HashMap<>();
        morphParams.put(1, new ComponentMorphParameters(0.2));
        morphParams.put(2, new ComponentMorphParameters(0.2));


        MorphedMatchStick childMStick = new MorphedMatchStick();
        childMStick.setProperties(30.0);
        childMStick.genMorphedMatchStick(morphParams, parentMStick);
        ThreadUtil.sleep(500);
        drawPng(childMStick, 2L);

        System.out.println("Done");
    }

    private void drawPng(MatchStick matchStick, long id) {
        PNGmaker pngMaker = new PNGmaker(500, 500);
        pngMaker.createAndSavePNGsfromObjs(Arrays.asList(matchStick), Arrays.asList(new Long[]{id}), testBin);
    }

    @Test
    public void compare(){
        Map<Integer, ComponentMorphParameters> morphParams = new HashMap<>();
//        morphParams.put(1, new ComponentMorphParameters(0.0));
//        morphParams.put(2, new ComponentMorphParameters(0.0));

        MorphedMatchStick childMStick = new MorphedMatchStick();
        childMStick.setProperties(30.0);
        childMStick.genMorphedMatchStick(morphParams, parentMStick);

    }
}