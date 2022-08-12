package org.xper.acq;

import java.util.ArrayList;
import java.util.List;

import org.xper.Dependency;
import org.xper.acq.filter.AnalogFilter;
import org.xper.acq.filter.DigitalFilter;
import org.xper.acq.filter.HalfDigitalFilter;
import org.xper.acq.filter.QuadCenterDigitalFilter;
import org.xper.acq.filter.QuadDownDigitalFilter;
import org.xper.acq.filter.QuadUpDigitalFilter;
import org.xper.acq.vo.ChannelFilter;
import org.xper.acq.vo.ComediChannelSpec;
import org.xper.acq.vo.NiChannelSpec;
import org.xper.experiment.SystemVariableContainer;

public class AcqChannelFactory {
	@Dependency
	SystemVariableContainer variableContainer;
	@Dependency
	DataBuffer dataBuffer;
	
	ArrayList<NiChannelSpec> niChannelSpec;
	ArrayList<ComediChannelSpec> comediChannelSpec;
	ArrayList<ChannelFilter> channelFilterList;
	
	public void init () {
		// initialize NI channel specification
		niChannelSpec = new ArrayList<NiChannelSpec>();
		comediChannelSpec = new ArrayList<ComediChannelSpec>();
		channelFilterList = new ArrayList<ChannelFilter>();
		
		double masterFreq = Double.parseDouble(variableContainer.get("acq_master_frequency", 0));
		int n = Integer.parseInt(variableContainer.get("acq_n_channel", 0));
		for (int i = 0; i < n; i++) {
			short channel = Short.parseShort(variableContainer.get("acq_channel",
					i));
			NiChannelSpec niSpec = new NiChannelSpec();
			niSpec.setChannel(channel);
			double maxValue = Double.parseDouble(variableContainer.get(
					"acq_channel_max_value", channel));
			niSpec.setMaxValue(maxValue);
			double minValue = Double.parseDouble(variableContainer.get("acq_channel_min_value", channel));
			niSpec.setMinValue(minValue);
			niChannelSpec.add(niSpec);
			
			ComediChannelSpec comediSpec = new ComediChannelSpec();
			comediSpec.setChannel(channel);
			comediSpec.setMaxValue(maxValue);
			comediSpec.setMinValue(minValue);
			comediSpec.setAref(variableContainer.get("acq_channel_reference", channel));
			comediChannelSpec.add(comediSpec);
			
			String type = variableContainer.get("acq_channel_type", channel);
			
			if (type.equalsIgnoreCase("analog")) {
				initAnalogFilter(channel, masterFreq);
			} else if (type.equalsIgnoreCase("half_digital")) {
				HalfDigitalFilter filter = new HalfDigitalFilter();
				initDigitalFilter(filter, channel);
			} else if (type.equalsIgnoreCase("digital")) {
				DigitalFilter filter = new DigitalFilter();
				initDigitalFilter(filter, channel);
			} else if (type.equalsIgnoreCase("quad_center_digital")) {
				QuadCenterDigitalFilter filter = new QuadCenterDigitalFilter();
				initDigitalFilter(filter, channel);
			} else if (type.equalsIgnoreCase("quad_up_digital")) {
				QuadUpDigitalFilter filter = new QuadUpDigitalFilter();
				initDigitalFilter(filter, channel);
			} else if (type.equalsIgnoreCase("quad_down_digital")) {
				QuadDownDigitalFilter filter = new QuadDownDigitalFilter();
				initDigitalFilter(filter, channel);
			}
		}
	}
	
	void initDigitalFilter(DigitalFilter filter, short channel) {
		filter.setChannel(channel);
		filter.setDataBuffer(dataBuffer);
		double v0 = Double.parseDouble(variableContainer.get("acq_channel_digital_v0", channel));
		filter.setZeroThreshold(v0);
		double v1 = Double.parseDouble(variableContainer.get("acq_channel_digital_v1", channel));
		filter.setOneThreshold(v1);
		filter.init();
		channelFilterList.add(new ChannelFilter(channel, filter));
	}
	
	void initAnalogFilter(short channel, double masterFreq) {
		AnalogFilter filter = new AnalogFilter();
		filter.setChannel(channel);
		filter.setDataBuffer(dataBuffer);
		double freq = Double.parseDouble(variableContainer.get("acq_channel_frequency", channel));
		filter.setRecordEveryNSample((int)(masterFreq/freq));
		channelFilterList.add(new ChannelFilter(channel, filter));
	}

	public List<NiChannelSpec> getNiAcqChannels() {
		return niChannelSpec;
	}
	
	public List<ComediChannelSpec> getComediAcqChannels() {
		return comediChannelSpec;
	}
	
	public List<ChannelFilter> getAcqChannelFilter () {
		return channelFilterList;
	}

	public SystemVariableContainer getVariableContainer() {
		return variableContainer;
	}

	public void setVariableContainer(SystemVariableContainer variableContainer) {
		this.variableContainer = variableContainer;
	}

	public DataBuffer getDataBuffer() {
		return dataBuffer;
	}

	public void setDataBuffer(DataBuffer dataBuffer) {
		this.dataBuffer = dataBuffer;
	}
}
