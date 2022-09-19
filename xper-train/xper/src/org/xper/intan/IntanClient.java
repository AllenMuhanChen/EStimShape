package org.xper.intan;

import org.xper.Dependency;
import org.xper.exception.RemoteException;
import org.xper.time.TimeUtil;
import org.xper.util.ThreadUtil;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.ConnectException;
import java.net.Socket;
import java.nio.CharBuffer;

/**
 * @author Allen Chen
 *
 * Provides basic tcp communication with Intan, like connecting, get, set and executing commands
 */
public class IntanClient {
    static final int QUERY_INTERVAL_MS = 10;
    static final int TIME_OUT_MS = 1000;
    @Dependency
    String host = "172.30.9.78";

    @Dependency
    int port = 5000;

    @Dependency
    TimeUtil timeUtil;

    private PrintWriter out;
    private BufferedReader in;
    private Socket client;

    public void connect(){
        try {
            client = new Socket(host,port);
            out = new PrintWriter(client.getOutputStream(), true);
            in = new BufferedReader(new InputStreamReader(client.getInputStream()));
        } catch (ConnectException ce) {
            if (client.isConnected()){
                System.err.println("Connection Already Established");
            } else{
                throw new RemoteException(ce);
            }
        } catch (Exception e){
            throw new RemoteException(e);
        }
    }

    public void set(String parameter, String value) {
        String msg = "set " + parameter + " " + value;
        out.println(msg);

        //Wait until the correct value has been set
        waitFor(new Condition() {
            @Override
            public boolean check() {
                System.out.println("Waiting for value set on " + parameter + " to " + value);
                return get(parameter).equalsIgnoreCase(value);
            }
        });
    }

    /**
     * @param condition - given as a Boolean Operator - a function that returns a bool
     *
     * This is used to verify a set operation changes the value successfuly before
     * moving on because there is latency with setting operations.
     */
    public void waitFor(Condition condition) {
        ThreadUtil.sleep(QUERY_INTERVAL_MS);
        while (!condition.check()) {
            ThreadUtil.sleep(QUERY_INTERVAL_MS);
        }
    }

    public void clear(String parameter) {
        String msg = "set " + parameter;
        out.println(msg);
        waitFor(new Condition() {
            @Override
            public boolean check() {
                return isBlank(parameter);
            }
        });
    }

    /**
     * @param parameter
     * @return true if the specified parameter is not set in the Intan Software
     */
    public boolean isBlank(String parameter) {
        return get(parameter).isEmpty();
    }

    public String get(String parameter){
        out.println("get " + parameter);
        try {
            return readResponse(parameter);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }


    }

    private String readResponse(String parameter) throws IOException {
        long startTime = timeUtil.currentTimeMicros();
        while (timeUtil.currentTimeMicros() < startTime + TIME_OUT_MS*1000){
            in = new BufferedReader(new InputStreamReader(client.getInputStream()));
            if (in.ready()){
                CharBuffer cb = CharBuffer.allocate(1000);
                in.read(cb);
                cb.flip();
                String resp = cb.toString();
                if (resp == null) {
                    break;
                }
                if(parseResponse(resp).equalsIgnoreCase(parameter)){
                    return "";
                } else {
                    return parseResponse(resp);
                }
            }
        }
        System.err.println("Could not get " + parameter + ". Timed out after " + TIME_OUT_MS + "ms.");
        return null;
    }

    /**
     * Intan Server gives response in form "Return: ParameterName Value"
     * This method parses the last word to get the Value
     * @param response
     * @return
     */
    private String parseResponse(String response){
        String[] words = response.split((" "));
        return words[words.length-1];
    }

    public void execute(String action, String parameter) {
        out.println("execute " + action + " " + parameter);
    }

    public void execute(String action){
        out.println("execute " + action);
    }

    public void disconnect(){
        try {
            in.close();
            out.close();
            client.close();
        } catch (IOException e){
            throw new RuntimeException(e);
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

    public TimeUtil getTimeUtil() {
        return timeUtil;
    }

    public void setTimeUtil(TimeUtil timeUtil) {
        this.timeUtil = timeUtil;
    }


}
