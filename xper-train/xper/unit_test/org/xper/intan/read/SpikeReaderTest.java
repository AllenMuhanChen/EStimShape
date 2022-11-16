package org.xper.intan.read;

import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.*;

public class SpikeReaderTest {

    private SpikeReader spikeReader;
    private String channelName;
    private String spikeDatPath;

    @Test
    public void testReadSpikeFile(){
        spikeReader.readSpikeFile();

        assertEquals(418924363, spikeReader.magicNumber);
        assertEquals(1, spikeReader.spikeFileVersionNumber);
        assertEquals("Test_221116_113949", spikeReader.filename);
        assertEquals(32, spikeReader.channelList.size());
        assertTrue(spikeReader.channelList.contains("B-000") && spikeReader.channelList.contains("B-031"));
        assertEquals(32, spikeReader.customChannelList.size());
        assertTrue(spikeReader.customChannelList.contains("B-000") && spikeReader.channelList.contains("B-031"));
        assertEquals(30000f, spikeReader.sampleRate, 0.0001);
        assertEquals(30, spikeReader.samplesPreDetect);
        assertEquals(60, spikeReader.samplesPostDetect);

        assertEquals(1304, spikeReader.spikesForChannel.get("B-000").size());
        assertEquals(.00003333333333333333, spikeReader.spikesForChannel.get("B-000").get(0).tstampSeconds, 0.001);
        assertEquals(1551, spikeReader.spikesForChannel.get("B-031").size());
    }

    @Test
    public void getSpikeRate(){
        spikeReader.readSpikeFile();

        double actualSpikeRate = spikeReader.getSpikeRate("B-000");

        int expectedNumSpikes = 1304;
        double expectedElapsedTime = 6.364666666666;
        double expectedSpikeRate = expectedNumSpikes/expectedElapsedTime;
        assertEquals(expectedSpikeRate, actualSpikeRate, 0.001);
    }


    @Before
    public void setUp() {
        spikeDatPath = "/home/r2_allen/Documents/EStimShape/dev_221110/spikefiles_dev_221110/Test_221116_113949/spike.dat";
        spikeReader = new SpikeReader(spikeDatPath);
        channelName = "B-000";
    }


}