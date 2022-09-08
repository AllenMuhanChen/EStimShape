package org.xper.intan;

import org.xper.exception.RemoteException;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.Socket;
import java.nio.CharBuffer;

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
        } catch (Exception e) {
            throw new RemoteException(e);
        }
    }

    public String sendMessage(String msg){
        out.println(msg);
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

    public void stopConnection(){
        try {
            in.close();
            out.close();
            client.close();
        } catch (IOException e){
            throw new RuntimeException(e);
        }
    }

}
