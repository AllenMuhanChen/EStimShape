package org.xper.trialsync;

import java.util.Map;

import org.xper.Dependency;
import org.xper.acq.device.AnalogOutDevice;
import org.xper.db.vo.SystemVariable;
import org.xper.util.DbUtil;

public class AnalogTrialSync implements TrialSync  {
	@Dependency
	AnalogOutDevice device;
	
	@Dependency
	DbUtil dbUtil;
	
//	static final double ON_VOLT = 5;
	static final double OFF_VOLT = 0;

	public void startTrialSyncPulse() {
		turnOnTrialSync();
	}
	
	public void stopTrialSyncPulse() {
		turnOffTrialSync();
	}
	
	void turnOnTrialSync () {
		Map<String, SystemVariable> var = dbUtil.readSystemVar("xper_fixation_sync_high_volt");
		int onVolt = Integer.parseInt(var.get("xper_fixation_sync_high_volt").getValue(0));
		device.write(new double[]{onVolt});
	}
	void turnOffTrialSync () {
		device.write(new double[]{OFF_VOLT});
	}

	public AnalogOutDevice getDevice() {
		return device;
	}
	
	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public void setDevice(AnalogOutDevice device) {
		this.device = device;
	}
}
