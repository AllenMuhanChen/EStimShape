package org.xper.intan;

import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.*;

public class IntanStimulationControllerTest {

    @Before
    public void setUp() throws Exception {
    }

    @Test
    public void tcpNameForIntanChannel() {
        String channelString = IntanStimulationController.tcpNameForIntanChannel(RHSChannel.A000);
        assertEquals("a-000", channelString);
    }
}