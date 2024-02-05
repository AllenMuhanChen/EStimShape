package org.xper.allen.drawing.ga;

import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.*;

public class GAMatchStickTest {

    private TestMatchStickDrawer testMatchStickDrawer;

    @Before
    public void setUp() throws Exception {
        testMatchStickDrawer = new TestMatchStickDrawer();
        testMatchStickDrawer.setup();
    }

    @Test
    public void test() {
        GAMatchStick gaMatchStick = new GAMatchStick();
        gaMatchStick.setProperties(5);
        gaMatchStick.genMatchStickRand();

        testMatchStickDrawer.drawMStick(gaMatchStick);
    }
}