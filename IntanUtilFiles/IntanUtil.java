package org.xper.util;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.SocketException;
import java.net.UnknownHostException;
import java.net.InetAddress;
import java.util.Scanner;
import java.sql.*;
import jssc.*;



public class IntanUtil {
    private DatagramSocket socket;
    private InetAddress address;
    private int port = 7755;
    private byte[] buff;    
    private int baudRate = 1000000;

    SerialPort serialPort;

    public IntanUtil() throws SocketException, UnknownHostException, SQLException, Exception {
        socket = new DatagramSocket();
        address = InetAddress.getByName("172.30.6.78");

        //Method getPortNames() returns an array of strings. Elements of the array is already sorted.
        String[] portNames = SerialPortList.getPortNames();
        int ndx = 0;
        System.out.print("Available serial ports :  ");

        for(int i = 0; i < portNames.length; i++){
            System.out.print(portNames[i] +  " ");
            if(portNames[i].contains("ACM")) {
            	ndx = i;
                System.out.println("\nusing " + portNames[ndx]);
            	break;
            }
        }
        
        serialPort = new SerialPort(portNames[ndx]);
        
        if(serialPort.isOpened()) {
            System.out.println("opened " + portNames[ndx]);
    		serialPort.purgePort(SerialPort.PURGE_RXCLEAR | SerialPort.PURGE_TXCLEAR);
        	serialPort.closePort();
        }
		serialPort.openPort();
        serialPort.setParams(baudRate, 
                SerialPort.DATABITS_8,
                SerialPort.STOPBITS_1,
                SerialPort.PARITY_NONE);	
    }


    public String receive() throws IOException {
        String testStr = "hello, this is a test!";
        buff = testStr.getBytes();

        DatagramPacket packet = new DatagramPacket(buff, buff.length);
        socket.receive(packet);
        String recvStr = new String(packet.getData(), 0, packet.getLength());
        System.out.println("JK 32342 IntanUtil received : " + recvStr);
        return recvStr;    
    }

    
    
    public void send(String inStr) throws IOException {
        buff = inStr.getBytes();

        DatagramPacket packet = new DatagramPacket(buff, buff.length, address, port);
        socket.send(packet);
    }
    

	public void trigger() throws SerialPortException {
		// 
		serialPort.writeString("!trigger\r\n\0");
		System.out.println("JK 365533  trigger()  ");
	}	
	

	public void shutdown() throws SerialPortException {
		//  
		serialPort.purgePort(SerialPort.PURGE_RXCLEAR | SerialPort.PURGE_TXCLEAR);
		serialPort.closePort();
	}	
	

	public void test() throws SerialPortException {
		try {
			this.send("a test string");
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
//		String specStr = "\"1\"\n" + 
//				"\"0\"\n" + 
//				"\"00\"\n" + 
//				"\"1\"\n" + 
//				"\"1000\"\n" + 
//				"\"1000\"\n" + 
//				"\"biphasic\"\n" + 
//				"\"cathodic\"\n" + 
//				"\"100\"\n" + 
//				"\"0\"\n" + 
//				"\"100\"\n" + 
//				"\"0\"";
//		
//    	//send(specStr);  

	}	



    public static void main(String args[]) throws IOException, SQLException, Exception {
        IntanUtil intan = new IntanUtil();
        Scanner sc = new Scanner(System.in);	
        
	System.out.print("enter - trigger, test, send, quit : ");

        while(true){
            String inStr = sc.nextLine();
                      
            if(inStr.equals("trigger"))
            	intan.trigger();
            
            else if(inStr.equals("test"))
            	intan.test();     
            else if(inStr.equals("send")) {
            	inStr = sc.nextLine();
            	intan.send(inStr);  
        		System.out.println(inStr);
            }
            
            else if(inStr.equals("quit"))
                break;                   
        }
        sc.close();
        intan.shutdown();
		System.out.println("finished");
    }
}

