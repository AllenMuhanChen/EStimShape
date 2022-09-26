package org.xper.acq;

import java.util.ArrayList;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.acq.device.AcqStreamingDevice;
import org.xper.exception.AcqException;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;
import org.xper.util.ThreadUtil;

public class DefaultAcqDeviceController implements AcqDeviceController {
	static Logger logger = Logger.getLogger(DefaultAcqDeviceController.class);

	@Dependency
	AcqStreamingDevice acqDevice;
	@Dependency
	int deviceBufferCount;
	@Dependency
	DataFilterController dataFilterController;
	@Dependency
	DataBuffer dataBuffer;
	@Dependency
	TimeUtil localTimeUtil;
	@Dependency
	DbUtil dbUtil;

	Thread acqThread;
	ExecutorService processingThread;
	AtomicBoolean done = new AtomicBoolean(false);
	AtomicBoolean stopping = new AtomicBoolean(false);
	ArrayBlockingQueue<double[]> rawBuffer;

	long startTime;
	long stopTime;

	public void init() {
		rawBuffer = new ArrayBlockingQueue<double[]>(deviceBufferCount);
	}

	public void connect() {
		acqDevice.connect();
	}

	public void disconnect() {
		acqDevice.disconnect();
	}

	public boolean isRunning() {
		return !done.get();
	}

	public void start() {
		startTime = localTimeUtil.currentTimeMicros();
		
		// Repair database just in case
		dbUtil.repairAcqSession(startTime);
		
		dbUtil.writeBeginAcqSession(startTime);

		dataBuffer.startSession();
		processingThread = Executors.newSingleThreadExecutor();
		
		dataFilterController.startSession();

		startAcqThread();

		System.out.println("Acq started: " + startTime);
	}

	void processRawData() {
		processingThread.execute(new Runnable() {
			public void run() {
				ArrayList<double []> data = new ArrayList<double []>();
				int n = rawBuffer.drainTo(data);
				for (double [] d: data) {
					dataFilterController.put(d);
					if (logger.isDebugEnabled()) {
						logger.debug("Data processed: " + n);
					}
				}
			}});
	}

	void startAcqThread() {
		acqThread = new Thread(new Runnable() {
			public void run() {
				done.set(false);
				stopping.set(false);

				acqDevice.start();
				while (!stopping.get()) {
					acquireData();
				}
				acquireData();
				acqDevice.stop();

				done.set(true);
			}
		});
		acqThread.start();
	}

	void acquireData() {
		double[] data = acqDevice.scan();
		if (data != null) {
			try {
				if (logger.isDebugEnabled()) {
					logger.debug("Data acquired: " + data.length);
				}
				rawBuffer.put(data);
			} catch (InterruptedException e) {
				throw new AcqException(
						"Overflow while putting raw data into buffer.", e);
			}
			
			processRawData();
		}
	}

	public void stop() {
		stopping.set(true);
		if (logger.isDebugEnabled()) {
			logger.debug("Trying to stop AcqServer... " + stopping.get());
		}
		if (acqThread != null) {
			try {
				acqThread.join();
			} catch (InterruptedException e) {
				e.printStackTrace();
			}
		}
		ThreadUtil.shutdownExecutorService(processingThread);

		dataFilterController.stopSession();
		dataBuffer.stopSession();

		stopTime = localTimeUtil.currentTimeMicros();
		dbUtil.writeEndAcqSession(startTime, stopTime);

		System.out.println("Acq stopped: " + stopTime);
	}

	public AcqStreamingDevice getAcqDevice() {
		return acqDevice;
	}

	public void setAcqDevice(AcqStreamingDevice acqDevice) {
		this.acqDevice = acqDevice;
	}

	public int getDeviceBufferCount() {
		return deviceBufferCount;
	}

	public void setDeviceBufferCount(int deviceBufferCount) {
		this.deviceBufferCount = deviceBufferCount;
	}

	public DataFilterController getDataFilterController() {
		return dataFilterController;
	}

	public void setDataFilterController(
			DataFilterController dataFilterController) {
		this.dataFilterController = dataFilterController;
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}

	public DbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public DataBuffer getDataBuffer() {
		return dataBuffer;
	}

	public void setDataBuffer(DataBuffer dataBuffer) {
		this.dataBuffer = dataBuffer;
	}
}
