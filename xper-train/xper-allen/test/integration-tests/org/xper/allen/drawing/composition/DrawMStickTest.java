package org.xper.allen.drawing.composition;


import static org.junit.Assert.fail;
import static org.xper.drawing.TestDrawingWindow.initXperLibs;

import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import org.xper.alden.drawing.drawables.PNGmaker;
import org.xper.drawing.stick.MatchStick;
import org.xper.util.ThreadUtil;
import org.xper.utils.RGBColor;

import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

public class DrawMStickTest {

    private String unit;
    private String xml_path;

    @Before
    public void before() throws Exception {
        initXperLibs();
//      unit = "170624_r-177";
//      unit = "170508_r-45";
//      unit = "170808_r-276";
        unit = "170807_r-274";
        xml_path = "/home/r2_allen/Documents/Ram GA/" + unit + "/top_stimulus.txt";
    }

    @Test
    public void test() {
        List<MatchStick> objs = new LinkedList<>();
        MatchStick mStick = new MatchStick();
        mStick.genMatchStickFromFile(xml_path);
        objs.add(mStick);

        PNGmaker pngMaker = new PNGmaker(500, 500);
        pngMaker.createAndSavePNGsfromObjs(objs, Arrays.asList(new Long[]{1L}), "/home/r2_allen/Documents/Ram GA/" + unit);
        ThreadUtil.sleep(1000);
    }

    @Test
    public void loadCSVandConvert(){


    }


}