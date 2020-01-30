package org.xper.util;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.DatagramPacket;
import java.net.InetAddress;
import java.net.MulticastSocket;
import java.util.ArrayList;
import java.util.List;

import org.xper.db.vo.BehMsgEntry;
import org.xper.exception.RuntimeIOException;

public class SocketUtil {
	
	public static byte[] encodeBehMsgEntry(BehMsgEntry ent) {
		try {
			ByteArrayOutputStream buf = new ByteArrayOutputStream();
			DataOutputStream out = new DataOutputStream(buf);

			out.writeLong(ent.getTstamp());
			out.writeUTF(ent.getType());
			out.writeUTF(ent.getMsg());
			return buf.toByteArray();
		} catch (IOException e) {
			throw new RuntimeIOException(e);
		}
	}
	
	public static List<BehMsgEntry> decodeBehMsgEntry (byte [] data) {
		ArrayList<BehMsgEntry> result = new ArrayList<BehMsgEntry>();
		
		ByteArrayInputStream buf = new ByteArrayInputStream(data);
		DataInputStream in = new DataInputStream(buf);
		
		try {
			while(in.available() > 0) {
				BehMsgEntry ent = new BehMsgEntry();
				ent.setTstamp(in.readLong());
				ent.setType(in.readUTF());
				ent.setMsg(in.readUTF());
				result.add(ent);
			}
		} catch (IOException e) {
			throw new RuntimeIOException(e);
		}
		return result;
	}

	public static void sendDatagramPacket(MulticastSocket s, byte[] packet,
			String addr, int port) {
		InetAddress group;
		try {
			group = InetAddress.getByName(addr);
			DatagramPacket msg = new DatagramPacket(packet, packet.length,
					group, port);
			s.send(msg);
		} catch (Exception e) {
			// It's OK for datagram packets to be lost.
		}
	}
}
