package org.xper.mockxper;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.xper.db.vo.AcqDataEntry;
import org.xper.db.vo.SystemVariable;
import org.xper.db.vo.TaskSpikeRate;
import org.xper.exception.VariableNotFoundException;

public class MockMarkerChannel implements MockChannel {
	int sampleInd;
	boolean even;
	
	public MockMarkerChannel() {
		sampleInd = INIT_SAMPLE_INDEX;
		even = true;
	}
	
	public List<AcqDataEntry> getData(TaskSpikeRate task, Map<String, SystemVariable> systemVar) {
		SystemVariable v = systemVar.get("xper_inter_slide_interval");
		double ifi = Double.parseDouble(v.getValues().get(0));
		
		v = systemVar.get("xper_slide_length");
		double slideLen = Double.parseDouble(v.getValues().get(0));
		
		int slideCount = (int)(slideLen * REFRESH_RATE / 1000);
		slideLen = slideCount * 1000.0 / (double)REFRESH_RATE;
		
		if (even) {
			v = systemVar.get("acq_even_marker_chan");
		} else {
			v = systemVar.get("acq_odd_marker_chan");
		}
		if (v == null) {
			throw new VariableNotFoundException("acq_even_marker_chan or acq_odd_marker_chan");
		}
		short chan = Short.parseShort(v.getValues().get(0));
		
		v = systemVar.get("acq_master_frequency");
		int freq = Integer.parseInt(v.getValues().get(0));
		
		int slideInterval = freq / REFRESH_RATE;
		int upTime = slideInterval / 2;
		
		int newSampleInd = (int)(sampleInd + ((slideLen + ifi) * freq / 1000));
		
		ArrayList<AcqDataEntry> result = new ArrayList<AcqDataEntry> ();
		for (int i = 0; i < slideCount; i ++) {
			AcqDataEntry up = new AcqDataEntry ();
			up.setChannel(chan);
			up.setSampleInd(sampleInd + i*slideInterval);
			up.setValue (2);
			result.add(up);
			
			AcqDataEntry down = new AcqDataEntry ();
			down.setChannel (chan);
			down.setSampleInd (up.getSampleInd() + upTime);
			down.setValue ( -2);
			result.add(down);
		}
		sampleInd = newSampleInd;
		
		even = !even;
		return result;
	}
	
	public void sessionInit () {
		sampleInd = INIT_SAMPLE_INDEX;
	}
}
