package org.xper.acq;

import java.util.List;

import org.xper.Dependency;
import org.xper.acq.filter.DataFilter;
import org.xper.acq.vo.ChannelFilter;

public class DefaultDataFilterController implements DataFilterController {

	/**
	 * One data filter might handle multiple channels. Lists the filter for each channel.
	 */
	@Dependency
	List<ChannelFilter> channelFilterList;
	@Dependency
	int sessionStartSampleIndex = 0;
	
	int scanIndex;
	/**
	 * Since the data for each scan does not come at once for some drivers, 
	 * a channelIndex need to be maintained.
	 */
	int channelIndex;
	
	public void startSession() {
		scanIndex = sessionStartSampleIndex;
		channelIndex = 0;
	}

	public void stopSession() {
		// reset filters for next acq session
		for (ChannelFilter ent : channelFilterList) {
			ent.getFilter().init();
		}
	}

	public void put(double[] data) {
		int i = 0;
		while (i < data.length) {
			ChannelFilter ent = channelFilterList.get(channelIndex);
			short chan = ent.getChannel();
			DataFilter filter = ent.getFilter();
			double value = data[i];
			filter.filter(chan, scanIndex, sessionStartSampleIndex, value);
			channelIndex ++;
			if (channelIndex == channelFilterList.size()) {
				scanIndex ++;
				channelIndex = 0;
			}
			i++;
		}
	}

	public int getSessionStartSampleIndex() {
		return sessionStartSampleIndex;
	}

	public void setSessionStartSampleIndex(int sessionStartSampleIndex) {
		this.sessionStartSampleIndex = sessionStartSampleIndex;
	}

	public List<ChannelFilter> getChannelFilterList() {
		return channelFilterList;
	}

	public void setChannelFilterList(List<ChannelFilter> channelFilterList) {
		this.channelFilterList = channelFilterList;
	}

	

}
