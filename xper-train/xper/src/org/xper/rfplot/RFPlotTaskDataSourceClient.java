package org.xper.rfplot;

import java.io.DataOutputStream;
import java.net.Socket;

import org.xper.Dependency;
import org.xper.exception.RemoteException;

public class RFPlotTaskDataSourceClient implements RFPlotClient {
	@Dependency
	String host;
	@Dependency
	int port = RFPlotTaskDataSource.DEFAULT_RF_PLOT_TASK_DATA_SOURCE_PORT;
	
	@Override
	public String getHost() {
		return host;
	}

	@Override
	public void setHost(String host) {
		this.host = host;
	}

	@Override
	public int getPort() {
		return port;
	}

	@Override
	public void setPort(int port) {
		this.port = port;
	}

	public RFPlotTaskDataSourceClient(String host, int port) {
		this.host = host;
		this.port = port;
	}

	public RFPlotTaskDataSourceClient(String host) {
		this.host = host;
	}
	
	@Override
	public void shutdownRFPlotTaskDataSourceServer() {
		Socket client;
		try {
			client = new Socket(host, port);
			DataOutputStream os = new DataOutputStream(client.getOutputStream());
			os.writeInt(RFPlotTaskDataSource.RFPLOT_STOP);
			os.close();
			client.close();
		} catch (Exception e) {
			throw new RemoteException(e);
		}
	}

	@Override
	public void changeRFPlotStim(String stim) {
		Socket client;
		try {
			client = new Socket(host, port);
			DataOutputStream os = new DataOutputStream(client.getOutputStream());
			os.writeInt(RFPlotTaskDataSource.RFPLOT_STIM_SPEC);
			os.writeUTF(stim);
			os.close();
			client.close();
		} catch (Exception e) {
			throw new RemoteException(e);
		}
	}
	
	@Override
	public void changeRFPlotXfm(String xfm) {
		Socket client;
		try {
			client = new Socket(host, port);
			DataOutputStream os = new DataOutputStream(client.getOutputStream());
			os.writeInt(RFPlotTaskDataSource.RFPLOT_XFM_SPEC);
			os.writeUTF(xfm);
			os.close();
			client.close();
		} catch (Exception e) {
			throw new RemoteException(e);
		}
	}
}
