package org.xper.allen.ga3d.blockgen;

import org.junit.BeforeClass;
import org.junit.Test;

import static org.junit.Assert.*;

public class MorphTrialTest {
    GA3DBlockGen generator = new GA3DBlockGen();

    @BeforeClass
    public void setUp(){

    }

    @Test
    public void write() {
        long testParentId = 1;
        MorphTrial morphTrial= new MorphTrial(generator, testParentId);

        morphTrial.write();

        assertMakesNewTrial();

    }

    private void assertMakesNewTrial() {
        fail();
    }
}