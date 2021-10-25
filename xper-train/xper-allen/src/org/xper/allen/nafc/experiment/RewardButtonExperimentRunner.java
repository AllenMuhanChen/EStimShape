package org.xper.allen.nafc.experiment;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.Socket;

import org.xper.Dependency;
import org.xper.experiment.ExperimentRunner;
import org.xper.juice.Juice;

public class RewardButtonExperimentRunner extends ExperimentRunner{
	@Dependency
	Juice juice;
	public static final int REWARD=4;
	
	@Override
	protected void handleCommand() throws IOException {
		System.out.println("Experiment Runner handleCommand() Called");
		Socket con = server.accept();
		try {
			DataInputStream is = new DataInputStream(con.getInputStream());
			int command = is.readInt();
			switch (command) {
			case PAUSE:
				experiment.setPause(true);
				break;
			case RESUME:
				experiment.setPause(false);
				break;
			case STOP:
				experiment.stop();
				done = true;
				break;
			case REWARD:
				System.out.println("REWARD COMMAND ON EXPERIMENTRUNNER");
				juice.deliver();
			}
			DataOutputStream os = new DataOutputStream(con.getOutputStream());
			os.writeInt(0);
		} finally {
			try {
				con.close();
			} catch (Exception e) {
				logger.warn(e.getMessage());
				e.printStackTrace();
			}
		}
	}
	public Juice getJuice() {
		return juice;
	}
	public void setJuice(Juice juice) {
		this.juice = juice;
	}
}
