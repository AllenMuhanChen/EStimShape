package org.xper.acq.vo;

public class NiChannelSpec {
	short channel;
	double minValue;
	double maxValue;
	
	public double getMinValue() {
		return minValue;
	}
	public void setMinValue(double minValue) {
		this.minValue = minValue;
	}
	public double getMaxValue() {
		return maxValue;
	}
	public void setMaxValue(double maxValue) {
		this.maxValue = maxValue;
	}
	public short getChannel() {
		return channel;
	}
	public void setChannel(short channel) {
		this.channel = channel;
	}
}
