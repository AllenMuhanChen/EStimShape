package org.xper.acq.player;

import java.util.ArrayList;
import java.util.List;

import org.xper.acq.player.AnalogChannelPlayer;
import org.xper.db.vo.AcqDataEntry;

import junit.framework.TestCase;

public class AnalogChannelPlayerTest extends TestCase {

	public void testSeekBegin() {
		List<AcqDataEntry> data = new ArrayList<AcqDataEntry>();
		int chan = 0;
		AnalogChannelPlayer player = new AnalogChannelPlayer(data, chan);
		assertFalse(player.seekBeginWith(0));
		
		AcqDataEntry e = new AcqDataEntry();
		e.setChannel((short)0);
		e.setSampleInd ( 0);
		data.add(e);
		assertTrue(player.seekBeginWith(0));
		
		e = new AcqDataEntry();
		e.setChannel ( (short)1);
		e.setSampleInd ( 1);
		data.add(e);
		
		assertFalse(player.seekBeginWith(1));
		
		e = new AcqDataEntry();
		e.setChannel ( (short)0);
		e.setSampleInd ( 2);
		data.add(e);
		
		assertTrue(player.seekBeginWith(1));
	}
	
	public void testNext () {
		List<AcqDataEntry> data = new ArrayList<AcqDataEntry>();
		int chan = 0;
		AnalogChannelPlayer player = new AnalogChannelPlayer(data, chan);
		
		AcqDataEntry e = new AcqDataEntry();
		e.setChannel ( (short)0);
		e.setSampleInd ( 0);
		data.add(e);
		
		e = new AcqDataEntry();
		e.setChannel ( (short)1);
		e.setSampleInd ( 1);
		data.add(e);
		
		e = new AcqDataEntry();
		e.setChannel ( (short)0);
		e.setSampleInd ( 2);
		data.add(e);
		
		assertTrue(player.seekBeginWith(0));
		
		assertEquals(2, player.next().getSampleInd());
	}
}
