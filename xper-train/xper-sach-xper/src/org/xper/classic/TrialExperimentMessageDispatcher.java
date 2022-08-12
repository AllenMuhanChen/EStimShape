package org.xper.classic;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.MulticastSocket;
import java.util.ArrayList;
import java.util.concurrent.ConcurrentLinkedQueue;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.classic.vo.SlideEvent;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialStatistics;
import org.xper.db.vo.BehMsgEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.exception.OverflowException;
import org.xper.exception.RemoteException;
import org.xper.exception.RuntimeIOException;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.experiment.listener.MessageDispatcher;
import org.xper.eye.listener.EyeDeviceMessageListener;
import org.xper.eye.listener.EyeEventListener;
import org.xper.eye.vo.EyeDeviceMessage;
import org.xper.eye.vo.EyePosition;
import org.xper.eye.vo.EyeWindowMessage;
import org.xper.eye.vo.EyeZeroMessage;
import org.xper.eye.win.EyeWindowMessageListener;
import org.xper.eye.zero.EyeZeroMessageListener;
import org.xper.util.DbUtil;
import org.xper.util.SocketUtil;
import org.xper.util.ThreadHelper;

/**
 * Save messages to database, then broadcast them.
 * 
 * @author john
 *
 */
public class TrialExperimentMessageDispatcher implements ExperimentEventListener,
		SlideEventListener, TrialEventListener, EyeEventListener,
		EyeDeviceMessageListener, EyeWindowMessageListener,
		EyeZeroMessageListener, MessageDispatcher {
	static Logger logger = Logger.getLogger(TrialExperimentMessageDispatcher.class);

	static final int DEFAULT_DISPATCH_INTERVAL = 100;
	public final static int PORT = 8900;
	public final static String GROUP = "228.8.8.8";
	public final static int TTL = 1;
	public final static int PACKET_SIZE = 1024;

	@Dependency
	DbUtil dbUtil = null;
	@Dependency
	long dispatchInterval = DEFAULT_DISPATCH_INTERVAL;
	@Dependency
	int port = PORT;
	@Dependency
	String group = GROUP;
	@Dependency
	int packetSize = PACKET_SIZE;
	@Dependency
	String host;

	protected TrialStatistics trialStat = new TrialStatistics();
	ConcurrentLinkedQueue<BehMsgEntry> messageQueue = new ConcurrentLinkedQueue<BehMsgEntry>();
	ThreadHelper threadHelper = new ThreadHelper("MessageDispatcher", this);

	protected void enqueue(long tstamp, String type, String msg) {
		BehMsgEntry ent = new BehMsgEntry();
		ent.setTstamp(tstamp);
		ent.setType(type);
		ent.setMsg(msg);

		messageQueue.add(ent);
	}

	public void experimentStart(long timestamp) {
		enqueue(timestamp, "ExperimentStart", "");

		trialStat.reset();
	}

	public void experimentStop(long timestamp) {
		enqueue(timestamp, "ExperimentStop", "");
	}

	public void slideOff(int index, long timestamp, int frameCount) {
		enqueue(timestamp, "SlideOff", SlideEvent
				.toXml(new SlideEvent(index, timestamp, frameCount)));
	}

	public void slideOn(int index, long timestamp) {
		enqueue(timestamp, "SlideOn", SlideEvent
				.toXml(new SlideEvent(index, timestamp, -1)));
	}

	public void eyeInBreak(long timestamp, TrialContext context) {
		enqueue(timestamp, "EyeInBreak", "");
		trialStat.setBrokenTrials(trialStat.getBrokenTrials()+1);
	}

	public void eyeInHoldFail(long timestamp, TrialContext context) {
		enqueue(timestamp, "EyeInHoldFail", "");
		trialStat.setFailedTrials(trialStat.getFailedTrials()+1);
	}

	public void fixationPointOn(long timestamp, TrialContext context) {
		enqueue(timestamp, "FixationPointOn", "");
	}

	public void fixationSucceed(long timestamp, TrialContext context) {
		enqueue(timestamp, "FixationSucceed", "");
	}

	public void initialEyeInFail(long timestamp, TrialContext context) {
		enqueue(timestamp, "InitialEyeInFail", "");
		trialStat.setFailedTrials(trialStat.getFailedTrials()+1);
	}

	public void initialEyeInSucceed(long timestamp, TrialContext context) {
		enqueue(timestamp, "InitialEyeInSucceed", "");
	}

	public void trialComplete(long timestamp, TrialContext context) {
		enqueue(timestamp, "TrialComplete", "");
		trialStat.setCompleteTrials(trialStat.getCompleteTrials() + 1);
	}
	
	public void trialInit(long timestamp, TrialContext context) {
		enqueue(timestamp, "TrialInit", "");
	}

	public void trialStart(long timestamp, TrialContext context) {
		enqueue(timestamp, "TrialStart", "");
	}

	public void trialStop(long timestamp, TrialContext context) {
		enqueue(timestamp, "TrialStop", "");
		enqueue(timestamp, "TrialStatistics",
				TrialStatistics.toXml(trialStat));
	}

	public void eyeIn(EyePosition eyePos, long timestamp) {
		enqueue(timestamp, "EyeInEvent", EyePosition
				.toXml(eyePos));
	}

	public void eyeOut(EyePosition eyePos, long timestamp) {
		enqueue(timestamp, "EyeOutEvent", EyePosition
				.toXml(eyePos));
	}

	public void eyeDeviceMessage(long timestamp, String id, Coordinates2D volt,
			Coordinates2D degree) {
		enqueue(timestamp, "EyeDeviceMessage",
				EyeDeviceMessage.toXml(new EyeDeviceMessage(timestamp, id,
						volt, degree)));
	}

	public void eyeWindowMessage(long timestamp,
			Coordinates2D center, double size) {
		enqueue(timestamp, "EyeWindowMessage",
				EyeWindowMessage.toXml(new EyeWindowMessage(timestamp,
						center, size)));
	}

	public void eyeZeroMessage(long timestamp, String id, Coordinates2D zero) {
		enqueue(timestamp, "EyeZeroMessage",
				EyeZeroMessage.toXml(new EyeZeroMessage(timestamp, id, zero)));
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
			threadHelper.join();
		}
	}

	void broadcastMessages(MulticastSocket s, ArrayList<BehMsgEntry> msgs) {
		if (s != null && msgs != null && msgs.size() > 0) {
			try {
				ByteArrayOutputStream out = new ByteArrayOutputStream(
						packetSize);
				for (BehMsgEntry msg : msgs) {
					byte[] data = SocketUtil.encodeBehMsgEntry(msg);
					if (data.length > packetSize) {
						throw new OverflowException(
								"packet size too small, expected size: "
										+ data.length);
					}
					if (out.size() + data.length > packetSize) {
						out.close();
						SocketUtil.sendDatagramPacket(s, out.toByteArray(),
								group, port);

						out = new ByteArrayOutputStream(packetSize);
					}

					out.write(data);
				}
				if (out.size() > 0) {
					out.close();
					SocketUtil.sendDatagramPacket(s, out.toByteArray(), group,
							port);
				}
			} catch (IOException e) {
				throw new RuntimeIOException(e);
			}
		}
	}

	public void run() {
		MulticastSocket s = null;
		try {
			s = new MulticastSocket();
			s.setTimeToLive(TTL);
			s.setInterface(InetAddress.getByName(host));
			if (logger.isDebugEnabled()) {
				logger.debug("Local socket: " + s.getLocalSocketAddress());
			}

			threadHelper.started();

			while (!threadHelper.isDone() || !messageQueue.isEmpty()) {
				// get all messages.
				ArrayList<BehMsgEntry> msgs = new ArrayList<BehMsgEntry>();
				BehMsgEntry ent = messageQueue.poll();
				while (ent != null) {
					if (logger.isDebugEnabled()) {
						logger.debug(ent.getTstamp() + ", " + ent.getType() + ","
								+ ent.getMsg());
					}
					msgs.add(ent);
					ent = messageQueue.poll();
				}
				// write to database
				if (dbUtil != null) {
					if (msgs.size() > 0) {
						BehMsgEntry[] arr = new BehMsgEntry[msgs.size()];
						msgs.toArray(arr);
//						dbUtil.writeBehMsgBatch(arr);
						dbUtil.writeBehMsgBatch(msgs);
					}
				}
				// broadcast the messages.
				broadcastMessages(s, msgs);

				try {
					Thread.sleep(dispatchInterval);
				} catch (InterruptedException e) {
				}
			}
		} catch (IOException e) {
			throw new RemoteException(
					"MessageDispatcher: cannot create multicast socket.", e);
		} finally {
			try {
				if (s != null) {
					s.close();
				}

				threadHelper.stopped();
			} catch (Exception e) {
				logger.warn(e.getMessage());
				e.printStackTrace();
			}
		}
	}

	public DbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public long getDispatchInterval() {
		return dispatchInterval;
	}

	public void setDispatchInterval(long dispatchInterval) {
		this.dispatchInterval = dispatchInterval;
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
	
	public String getHost() {
		return host;
	}

	public void setHost(String host) {
		this.host = host;
	}

}
