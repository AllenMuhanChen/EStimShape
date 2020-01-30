package org.xper.acq;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.db.vo.AcqDataEntry;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;
import org.xper.util.ThreadUtil;

public class DatabaseDataBuffer implements DataBuffer {
	static Logger logger = Logger.getLogger(DatabaseDataBuffer.class);

	@Dependency
	DbUtil dbUtil;
	/**
	 * Since global time server is deployed with acquisition server, we could
	 * use IndexedJdkTimeUtil instead of SocketTimeClient
	 */
	@Dependency
	TimeUtil localTimeUtil;
	@Dependency
	int blockSize;

	ExecutorService workerThread;
	List<AcqDataEntry> buffer = new ArrayList<AcqDataEntry>();

	class Task implements Runnable {
		DbUtil dbUtil;
		List<AcqDataEntry> data;
		TimeUtil timeUtil;

		public Task(DbUtil dbUtil, List<AcqDataEntry> data, TimeUtil timeUtil) {
			this.dbUtil = dbUtil;
			this.data = data;
			this.timeUtil = timeUtil;
		}

		public void run() {
			long tstamp = timeUtil.currentTimeMicros();
			dbUtil.writeAcqData(tstamp, data);
			if (logger.isDebugEnabled()) {
				logger.debug("writing AcqData: " + data.size());
			}
		}
	}

	public void put(short channel, int sampleInd, double value) {
		AcqDataEntry entry = new AcqDataEntry();
		entry.setChannel(channel);
		entry.setSampleInd(sampleInd);
		entry.setValue(value);
		buffer.add(entry);

		if (buffer.size() >= blockSize) {
			flushBuffer();
		}
	}
	
	void flushBuffer () {
		workerThread.execute(new Task(dbUtil, buffer, localTimeUtil));
		buffer = new ArrayList<AcqDataEntry>();
	}

	public void startSession() {
		workerThread = Executors.newSingleThreadExecutor();
	}

	public void stopSession() {
		if (buffer.size() > 0) {
			flushBuffer ();
		}
		ThreadUtil.shutdownExecutorService(workerThread);
	}

	public DbUtil getDbUtil() {
		return dbUtil;
	}

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}

	public int getBlockSize() {
		return blockSize;
	}

	public void setBlockSize(int blockSize) {
		this.blockSize = blockSize;
	}

}
