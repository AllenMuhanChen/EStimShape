package org.xper.fixtrain.console;

import org.xper.Dependency;
import org.xper.exception.RemoteException;
import org.xper.fixtrain.FixTrainTaskDataSource;

import java.io.DataOutputStream;
import java.net.Socket;

public class FixTrainClient {

    @Dependency
    String host;

    @Dependency
    int port = FixTrainTaskDataSource.DEFAULT_FIX_TRAIN_TASK_DATA_SOURCE_PORT;

    public void shutdownRFPlotTaskDataSourceServer(){
        Socket client;
        try {
            client = new Socket(host, port);
            DataOutputStream os = new DataOutputStream(client.getOutputStream());
            os.writeInt(FixTrainTaskDataSource.STOP);
            os.close();
            client.close();
        } catch (Exception e) {
            throw new RemoteException(e);
        }
    }

    public void changeStim(String stim) {
        Socket client;
        try {
            client = new Socket(host, port);
            DataOutputStream os = new DataOutputStream(client.getOutputStream());
            os.writeInt(FixTrainTaskDataSource.STIM_SPEC);
            os.writeUTF(stim);
            os.close();
            client.close();
        } catch (Exception e) {
            throw new RemoteException(e);
        }
    }

    public void changeXfm(String xfm){
        Socket client;
        try {
            client = new Socket(host, port);
            DataOutputStream os = new DataOutputStream(client.getOutputStream());
            os.writeInt(FixTrainTaskDataSource.XFM_SPEC);
            os.writeUTF(xfm);
            os.close();
            client.close();
        } catch (Exception e) {
            throw new RemoteException(e);
        }
    }

    public String getHost() {
        return host;
    }

    public void setHost(String host) {
        this.host = host;
    }

    public int getPort() {
        return port;
    }

    public void setPort(int port) {
        this.port = port;
    }
}