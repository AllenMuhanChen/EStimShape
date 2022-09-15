package org.xper.intan;

import org.xper.exception.RemoteException;

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
 * Provides base-level tcp communication with Intan, like connecting, get, set and executing commands
 */
public class IntanClient {
    String host = "172.30.9.78";
    int port = 5000;
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
    }

    public String get(String parameter){
        out.println("get " + parameter);
//
        try {
            while (true){
                if (in.ready()){
                    CharBuffer cb = CharBuffer.allocate(1000);
                    in.read(cb);
                    cb.flip();
                    String resp = cb.toString();
                    if (resp == null) {
                        break;
                    }
                    return resp;
                }
            }

        } catch (IOException e) {
            throw new RuntimeException(e);
        }

        return null;
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


//    public boolean isRunModeRun(){
//        return client.isConnected();
//    }

}
