package org.xper.allen.nafc.experiment;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;

import org.xper.Dependency;
import org.xper.exception.RemoteException;
import org.xper.experiment.ExperimentRunner;
import org.xper.juice.Juice;
import org.xper.util.DbUtil;

import org.xper.time.TimeUtil;;

public class RewardButtonExperimentRunner extends ExperimentRunner{
	@Dependency
	Juice juice;
	
	@Dependency
	DbUtil dbUtil;
	
	@Dependency
	TimeUtil timeUtil;
	public static final int REWARD=4;
	
	
	@Override
	protected void handleCommand() throws IOException {
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
				juice.deliver();
				dbUtil.writeExpLog(timeUtil.currentTimeMicros(), "Manual Reward Given via Console");
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
	
	protected void listen() {
		try {
			server = new ServerSocket(port, backlog, InetAddress.getByName(host));
			System.out.println("RewardButtonExperimentRunner started on host " + host + " port " + port);
			while (!done) {
				handleCommand();
			}
		} catch (Exception e) {
			if (experiment.isRunning()) {
				experiment.stop();
			}
			throw new RemoteException(e);
		} finally {
			try {
				server.close();
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

	public DbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public TimeUtil getTimeUtil() {
		return timeUtil;
	}

	public void setTimeUtil(TimeUtil timeUtil) {
		this.timeUtil = timeUtil;
	}
}
