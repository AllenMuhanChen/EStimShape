package org.xper.experiment.listener;

import java.util.Set;

import org.xper.Dependency;
import org.xper.util.OsUtil;

public class CpuBinder implements ExperimentEventListener {

	@Dependency
	Set<Integer> cpuSet;
	
	public void experimentStart(long timestamp) {
		OsUtil.setAffinity(cpuSet);
	}

	public void experimentStop(long timestamp) {
	}

	public Set<Integer> getCpuSet() {
		return cpuSet;
	}

	public void setCpuSet(Set<Integer> cpuSet) {
		this.cpuSet = cpuSet;
	}

}
