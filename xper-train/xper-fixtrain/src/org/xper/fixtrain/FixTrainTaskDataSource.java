package org.xper.fixtrain;

import org.xper.Dependency;
import org.xper.exception.RemoteException;
import org.xper.experiment.ExperimentTask;
import org.xper.experiment.TaskDataSource;
import org.xper.experiment.Threadable;
import org.xper.fixtrain.drawing.FixTrainDrawable;
import org.xper.util.ThreadHelper;

import java.io.DataInputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

public class FixTrainTaskDataSource implements TaskDataSource, Threadable {

    public static final int DEFAULT_FIX_TRAIN_TASK_DATA_SOURCE_PORT = 8893;
    private static final int DEFAULT_BACK_LOG = 10;
    public static final int STOP = 0;
    public static final int STIM_SPEC = 1;
    public static final int XFM_SPEC = 2;

    @Dependency
    int port = DEFAULT_FIX_TRAIN_TASK_DATA_SOURCE_PORT;

    @Dependency
    int backlog = DEFAULT_BACK_LOG;

    @Dependency
    String host;

    @Dependency
    Map<String, FixTrainDrawable> fixTrainObjectMap;

    ServerSocket server = null;
    AtomicReference<ExperimentTask> currentTask = new AtomicReference<ExperimentTask>();
    ThreadHelper threadHelper = new ThreadHelper("FixTrainTaskDataSource", this);

    @Override
    public ExperimentTask getNextTask() {
        ExperimentTask task = currentTask.get();
        if (task == null){
            task = new ExperimentTask();
        }
        if (task.getStimSpec() == null) {
            FixTrainDrawable firstStimObj = getFirstStimObj();
            task.setStimSpec(FixTrainStimSpec.getStimSpecFromFixTrainDrawable(firstStimObj));
        }
        if (task.getXfmSpec() == null){
            task.setXfmSpec(FixTrainXfmSpec.fromXml(null).toXml());
        }

        currentTask.set(task);
        return currentTask.get();

    }


    private FixTrainDrawable getFirstStimObj() {
        return (FixTrainDrawable) fixTrainObjectMap.values().toArray()[0];
    }

    @Override
    public void run() {
        try {
            server = new ServerSocket(port, backlog, InetAddress.getByName(host));
            System.out.println("FixTrainTaskDataSource started on host " + host + " port " + port);

            threadHelper.started();

            while (!threadHelper.isDone()) {
                handleRequest();
            }
        } catch (Exception e) {
            if (!threadHelper.isDone()) {
                throw new RemoteException(e);
            }
        } finally {
            try {
                threadHelper.stopped();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private void handleRequest() throws IOException {
        Socket con = null;
        try {
            con = server.accept();
            DataInputStream input = new DataInputStream(con.getInputStream());
            int response = input.readInt();

            if (response != STOP) {
                String spec = input.readUTF();

                ExperimentTask task = currentTask.get();
                if (task == null) {
                    task = new ExperimentTask();
                }

                switch (response) {
                    case STIM_SPEC:
                        task.setStimSpec(spec);
                        break;
                    case XFM_SPEC:
                        task.setXfmSpec(spec);
                        break;
                }
                currentTask.set(task);
            }
            input.close();

        } catch (SocketTimeoutException e) {
        } finally {
            try {
                if (con != null) {
                    con.close();
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    @Override
    public void stop() {
        if (isRunning()) {
            threadHelper.stop();
            try {
                server.close();
            } catch (Exception e) {
            }
            threadHelper.join();
        }
    }

    @Override
    public void ungetTask(ExperimentTask t) {

    }

    @Override
    public boolean isRunning() {
        return threadHelper.isRunning();
    }

    @Override
    public void start() {
        threadHelper.start();
    }

    public int getPort() {
        return port;
    }

    public void setPort(int port) {
        this.port = port;
    }

    public int getBacklog() {
        return backlog;
    }

    public void setBacklog(int backlog) {
        this.backlog = backlog;
    }

    public String getHost() {
        return host;
    }

    public void setHost(String host) {
        this.host = host;
    }

    public Map<String, FixTrainDrawable> getFixTrainObjectMap() {
        return fixTrainObjectMap;
    }

    public void setFixTrainObjectMap(Map<String, FixTrainDrawable> fixTrainObjectMap) {
        this.fixTrainObjectMap = fixTrainObjectMap;
    }
}