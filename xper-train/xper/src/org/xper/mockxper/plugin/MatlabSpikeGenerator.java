package org.xper.mockxper.plugin;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;

//import jmatlink.JMatLink;

import org.xper.Dependency;
import org.xper.mockxper.MockSpikeGenerator;

public class MatlabSpikeGenerator implements MockSpikeGenerator {
	@Dependency
	String matlabFunctionName = null;

//	JMatLink jmatlink = new JMatLink();

	public MatlabSpikeGenerator() {
	}

	protected boolean matlabFunctionValid() {
		if (matlabFunctionName == null)
			return false;
		if (matlabFunctionName.length() <= 0)
			return false;
		return true;
	}

	@PostConstruct
	public void connect() {
		if (matlabFunctionValid()) {
//			jmatlink.engOpen();
		}
	}

	@PreDestroy
	public void disconnect() {
		if (matlabFunctionValid()) {
//			jmatlink.engClose();
		}
	}

	public double getSpikeRate(long taskId) {
//		if (matlabFunctionValid()) {
//			String retName = "mockXperMatlabSpikeGeneratorReturn";
//			jmatlink.engOutputBuffer();
//			jmatlink.engEvalString(retName + " = " + matlabFunctionName + "("
//					+ taskId + ")");
//			double ret = jmatlink.engGetScalar(retName);
//			String output = jmatlink.engGetOutputBuffer();
//			System.out.println("Matlab: " + (output == null ? "" : output));
//			System.out.println("MatlabSpikeGenerator: taskId -> " + taskId
//					+ " spikeRate -> " + ret);
//			return ret;
//		} else {
			return 100.0;
//		}
	}

	public void setMatlabFunctionName(String matlabFunctionName) {
		this.matlabFunctionName = matlabFunctionName;
	}
}
