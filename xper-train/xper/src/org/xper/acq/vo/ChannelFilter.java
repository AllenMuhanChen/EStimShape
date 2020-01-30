package org.xper.acq.vo;

import org.xper.acq.filter.DataFilter;

public class ChannelFilter {
	short channel;
	DataFilter filter;
	public ChannelFilter(short channel, DataFilter filter) {
		super();
		this.channel = channel;
		this.filter = filter;
	}
	public short getChannel() {
		return channel;
	}
	public void setChannel(short channel) {
		this.channel = channel;
	}
	public DataFilter getFilter() {
		return filter;
	}
	public void setFilter(DataFilter filter) {
		this.filter = filter;
	}
}
