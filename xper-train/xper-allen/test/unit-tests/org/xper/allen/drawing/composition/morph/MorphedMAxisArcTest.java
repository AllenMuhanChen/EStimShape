package org.xper.allen.drawing.composition.morph;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;
import org.xper.XperConfig;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.drawing.TestDrawingWindow;
import org.xper.util.ThreadUtil;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

public class MorphedMAxisArcTest {
    private TestDrawingWindow window;
    public static final Vector3d VIEW_ABOVE = new Vector3d(0, 1, 0);
    @Before
    public void setUp() throws Exception {
        List<String> libs = new ArrayList<String>();
        libs.add("xper");
        new XperConfig("", libs);

        getTestDrawingWindow();
    }

    @Test
    @Ignore
    public void genMorphedArc() {
        MorphedMAxisArc arc = new MorphedMAxisArc();
        arc.genArc(100000, 5);
        arc.transRotMAxis(1, new Point3d(0,0,0), 1, VIEW_ABOVE, 0);

        MorphedMAxisArc morphedArc = new MorphedMAxisArc();
        ComponentMorphParameters morphParams = new ComponentMorphParameters(0.2, new MorphDistributer(1/3.0));
        morphedArc.genMorphedArc(arc, 1, morphParams);
//        morphedArc.transRotMAxis(1, new Point3d(0,0,0), 1, VIEW_ABOVE, 0);

        window.draw(new Drawable() {
            @Override
            public void draw() {
                arc.drawArc(1.0f, 1.0f, 0.0f);
                morphedArc.drawArc(0.0f, 1.0f, 1.0f);
            }
        });
        ThreadUtil.sleep(100000);
    }

    private TestDrawingWindow getTestDrawingWindow() {
        window = TestDrawingWindow.createDrawerWindow();
        return window;
    }
}