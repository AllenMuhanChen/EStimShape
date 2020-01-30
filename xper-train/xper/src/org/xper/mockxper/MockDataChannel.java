package org.xper.mockxper;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.xper.db.vo.AcqDataEntry;
import org.xper.db.vo.SystemVariable;
import org.xper.db.vo.TaskSpikeRate;
import org.xper.exception.VariableNotFoundException;

public class MockDataChannel implements MockChannel {
	int sampleInd;
	
	public MockDataChannel() {
		sampleInd = INIT_SAMPLE_INDEX;
	}
	
	public List<AcqDataEntry> getData(TaskSpikeRate task, Map<String, SystemVariable> systemVar) {
		SystemVariable v = systemVar.get("xper_inter_slide_interval");
		if (v == null) {
			throw new VariableNotFoundException("xper_inter_slide_interval");
		}
		double ifi = Double.parseDouble(v.getValues().get(0));
		
		v = systemVar.get("xper_slide_length");
		if (v == null) {
			throw new VariableNotFoundException("xper_slide_length");
		}
		double slideLen = Double.parseDouble(v.getValues().get(0));
		
		int slideCount = (int)(slideLen * REFRESH_RATE / 1000);
		slideLen = slideCount * 1000.0 / (double)REFRESH_RATE;
		
		v = systemVar.get("acq_data_chan");
		if (v == null) {
			throw new VariableNotFoundException("acq_data_chan");
		}
		short chan = Short.parseShort(v.getValues().get(0));
		
		v = systemVar.get("acq_master_frequency");
		if (v == null) {
			throw new VariableNotFoundException("acq_master_frequency");
		}
		int freq = Integer.parseInt(v.getValues().get(0));
		
		int spikeCount = (int)(task.getSpikeRate() * slideLen / 1000);
		if (spikeCount <= 0) spikeCount = 1;
		int lastslideInd = (int)(sampleInd + (slideLen * freq / 1000));
		int spikeInterval = (lastslideInd - sampleInd - 1) / spikeCount;
		
		int newSampleInd = (int)(sampleInd + ((slideLen + ifi) * freq / 1000));
		
		ArrayList<AcqDataEntry> result = new ArrayList<AcqDataEntry>();
		for (int i = 0; i < spikeCount; i ++) {
			AcqDataEntry up = new AcqDataEntry ();
			up.setChannel(chan);
			up.setSampleInd(sampleInd + i*spikeInterval);
			up.setValue(2);
			result.add(up);
			
			AcqDataEntry down = new AcqDataEntry ();
			down.setChannel(chan);
			down.setSampleInd(up.getSampleInd() + 1);
			down.setValue(-2);
			result.add(down);
		}
		
		sampleInd = newSampleInd;
		return result;
	}
	
	public void sessionInit () {
		sampleInd = INIT_SAMPLE_INDEX;
	}
}
