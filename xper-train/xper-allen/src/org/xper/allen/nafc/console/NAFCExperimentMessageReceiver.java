package org.xper.allen.nafc.console;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.InetAddress;
import java.net.MulticastSocket;
import java.util.List;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.allen.nafc.message.NAFCExperimentMessageDispatcher;
import org.xper.allen.nafc.message.NAFCExperimentMessageHandler;
import org.xper.console.ExperimentMessageHandler;
import org.xper.console.MessageReceiverEventListener;
import org.xper.db.vo.BehMsgEntry;
import org.xper.exception.RemoteException;
import org.xper.experiment.Threadable;
import org.xper.juice.Juice;
import org.xper.util.SocketUtil;
import org.xper.util.ThreadHelper;

public class NAFCExperimentMessageReceiver implements Threadable {
	static Logger logger = Logger.getLogger(NAFCExperimentMessageReceiver.class);
	
	@Dependency
	int port = NAFCExperimentMessageDispatcher.PORT;
	@Dependency
	String group = NAFCExperimentMessageDispatcher.GROUP;
	@Dependency
	int packetSize = NAFCExperimentMessageDispatcher.PACKET_SIZE;
	@Dependency
	List<MessageReceiverEventListener> messageReceiverEventListeners;
	@Dependency
	NAFCExperimentMessageHandler messageHandler;
	@Dependency
	String receiverHost;
	@Dependency
	String dispatcherHost;
	
	ThreadHelper threadHelper = new ThreadHelper("ExperimentMessageReceiver", this);
	MulticastSocket socket = null;

	public NAFCExperimentMessageReceiver() {
		super();
	}

	
	public boolean isRunning() {
		return threadHelper.isRunning();
	}

	public void start() {
		threadHelper.start();
	}

	public void stop() {
		if (isRunning()) {
			threadHelper.stop();
			try {
				socket.leaveGroup(InetAddress.getByName(group));
				socket.close();
			} catch (Exception e) {
			}
			threadHelper.join();
		}
	}

	protected void handleMessage(List<BehMsgEntry> msgs) {
		for (BehMsgEntry msg : msgs) {
			messageHandler.handleMessage(msg);
		}
	}

	void fireMessageEvent() {
		if (messageReceiverEventListeners != null) {
			for (MessageReceiverEventListener listener : messageReceiverEventListeners) {
				listener.messageReceived();
			}
		}
	}

	void receiveMessage() {
		byte buf[] = new byte[packetSize];
		DatagramPacket pack = new DatagramPacket(buf, buf.length);
		try {
			socket.receive(pack);
			if (pack.getAddress().equals(InetAddress.getByName(dispatcherHost))) {
				if (logger.isDebugEnabled()) {
					logger.debug("Packet from " + pack.getSocketAddress());
				}
				byte data[] = new byte[pack.getLength()];
				System.arraycopy(pack.getData(), pack.getOffset(), data, 0, pack
					.getLength());
				List<BehMsgEntry> msgs = SocketUtil.decodeBehMsgEntry(data);
				handleMessage(msgs);
				fireMessageEvent();
			} else {
				logger.info("Packet from " + pack.getSocketAddress() +" ignored.");
			}
		} catch (IOException e) {
			throw new RemoteException(e);
		}
	
	}

	public void run() {
		try {
			socket = new MulticastSocket(port);
			socket.setInterface(InetAddress.getByName(receiverHost));
			socket.joinGroup(InetAddress.getByName(group));
			if (logger.isDebugEnabled()) {
				logger.debug("Local socket: " + socket.getLocalSocketAddress());
			}
	
			threadHelper.started();
			while (!threadHelper.isDone()) {
				receiveMessage();
			}
		} catch (Exception e) {
			if (!threadHelper.isDone()) {
				throw new RemoteException(e);
			}
		} finally {
			try {
				threadHelper.stopped();
			} catch (Exception e) {
				logger.warn(e.getMessage());
				e.printStackTrace();
			}
		}
	}

	public String getGroup() {
		return group;
	}

	public void setGroup(String group) {
		this.group = group;
	}

	public int getPacketSize() {
		return packetSize;
	}

	public void setPacketSize(int packetSize) {
		this.packetSize = packetSize;
	}

	public int getPort() {
		return port;
	}

	public void setPort(int port) {
		this.port = port;
	}

	public List<MessageReceiverEventListener> getMessageReceiverEventListeners() {
		return messageReceiverEventListeners;
	}

	public void setMessageReceiverEventListeners(List<MessageReceiverEventListener> messageReceiverEventListeners) {
		this.messageReceiverEventListeners = messageReceiverEventListeners;
	}
	
	public void addMessageReceiverEventListener (MessageReceiverEventListener listener) {
		this.messageReceiverEventListeners.add(listener);
	}
	
	public void removeMessageReceiverEventListener (MessageReceiverEventListener listener) {
		this.messageReceiverEventListeners.remove(listener);
	}

	public ExperimentMessageHandler getMessageHandler() {
		return messageHandler;
	}

	public void setMessageHandler(NAFCExperimentMessageHandler messageHandler) {
		this.messageHandler = messageHandler;
	}

	public String getReceiverHost() {
		return receiverHost;
	}

	public void setReceiverHost(String receiverHost) {
		this.receiverHost = receiverHost;
	}

	public String getDispatcherHost() {
		return dispatcherHost;
	}

	public void setDispatcherHost(String dispatcherHost) {
		this.dispatcherHost = dispatcherHost;
	}



}