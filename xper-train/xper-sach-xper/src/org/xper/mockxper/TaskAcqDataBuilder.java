package org.xper.mockxper;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import org.xper.Dependency;
import org.xper.db.vo.AcqDataEntry;
import org.xper.db.vo.SystemVariable;
import org.xper.db.vo.TaskSpikeRate;
import org.xper.exception.MockAcqDataIOException;
import org.xper.util.DbUtil;

import com.mindprod.ledatastream.LEDataOutputStream;

public class TaskAcqDataBuilder {
	@Dependency
	DbUtil dbUtil;
	@Dependency
	MockDataChannel dataChan;
	@Dependency
	MockMarkerChannel markerChan;
	
	/**
	 * Merge {@link AcqDataEntry} data of two lists based on sample index order.
	 * 
	 * @param list 1
	 * @param list 2
	 * @return new combined list
	 */
	protected List<AcqDataEntry> mergeChannelData (List<AcqDataEntry> l1, List<AcqDataEntry> l2) {
		ArrayList<AcqDataEntry> result = new ArrayList<AcqDataEntry> ();
		for (AcqDataEntry l1ent : l1) {
			for (Iterator<AcqDataEntry> i2=l2.iterator();i2.hasNext();) {
				AcqDataEntry l2ent = (AcqDataEntry)i2.next();
				if (l2ent.getSampleInd() > l1ent.getSampleInd()) {
					break;
				}
				result.add(l2ent);
				i2.remove();
			}
			result.add(l1ent);
		}
		
		for (AcqDataEntry l2ent : l2) {
			result.add(l2ent);
		}
		return result;
	}
	
	protected void writeAcqDataEntry (LEDataOutputStream out, AcqDataEntry entry) throws IOException {
		out.writeShort(entry.getChannel());
		out.writeInt(entry.getSampleInd());
		out.writeDouble(entry.getValue());
	}

	public byte[] buildAcqData (TaskSpikeRate task) {
		Map<String, SystemVariable> systemVar = dbUtil.readSystemVar("%");
		ByteArrayOutputStream buf = new ByteArrayOutputStream();
		LEDataOutputStream out = new LEDataOutputStream(buf);
		try {
			List<AcqDataEntry> data = dataChan.getData(task,systemVar);
			List<AcqDataEntry> marker = markerChan.getData(task,systemVar);
			List<AcqDataEntry> result = mergeChannelData(data, marker);
			for (AcqDataEntry ent : result) {				
				writeAcqDataEntry(out,ent);
			}
			out.flush();
			out.close();
		} catch (IOException e) {
			throw new MockAcqDataIOException(e);
		}
		return buf.toByteArray();
	}
	
	public void sessionInit () {
		dataChan.sessionInit();
		markerChan.sessionInit();
	}

	public void setDataChan(MockDataChannel dataChan) {
		this.dataChan = dataChan;
	}

	public void setMarkerChan(MockMarkerChannel markerChan) {
		this.markerChan = markerChan;
	}

	public void setDbUtil(DbUtil dbUtil) {
		this.dbUtil = dbUtil;
	}
}
