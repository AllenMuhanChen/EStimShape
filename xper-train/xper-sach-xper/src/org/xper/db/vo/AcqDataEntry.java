package org.xper.db.vo;

public class AcqDataEntry {
	short channel;
	int sampleInd;
	double value;
	
	/**
	 * Size of the structure.
	 * 
	 * @return size as integer.
	 */
	public static int size () {
		return (Short.SIZE + Integer.SIZE + Double.SIZE)/8;
	}

	public short getChannel() {
		return channel;
	}

	public void setChannel(short channel) {
		this.channel = channel;
	}

	public int getSampleInd() {
		return sampleInd;
	}

	public void setSampleInd(int sampleInd) {
		this.sampleInd = sampleInd;
	}

	public double getValue() {
		return value;
	}

	public void setValue(double value) {
		this.value = value;
	}
}
