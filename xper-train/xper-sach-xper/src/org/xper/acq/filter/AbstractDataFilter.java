package org.xper.acq.filter;

import org.xper.Dependency;
import org.xper.acq.DataBuffer;


public abstract class AbstractDataFilter implements DataFilter {

	@Dependency
	protected DataBuffer dataBuffer;
	
	protected void record (short chan, int sampleIndex, double value) {
		dataBuffer.put(chan, sampleIndex, value);
	}
	
	public void init () {}

	public DataBuffer getDataBuffer() {
		return dataBuffer;
	}

	public void setDataBuffer(DataBuffer dataBuffer) {
		this.dataBuffer = dataBuffer;
	}

}
