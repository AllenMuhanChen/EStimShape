package org.xper.acq;

import java.util.List;
import java.util.Map;

import junit.framework.TestCase;

import org.junit.Ignore;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.xper.acq.vo.DigitalChannel;
import org.xper.db.vo.AcqDataEntry;
import org.xper.db.vo.SystemVariable;
import org.xper.util.DbUtil;
import org.xper.util.FileUtil;

import static org.junit.Assert.assertTrue;

@Ignore
public class AcqDataTest {
	public void testReadAcqData () {

		JavaConfigApplicationContext context = new JavaConfigApplicationContext(FileUtil.loadConfigClass("test.experiment.config_class"));
		DbUtil dbUtil = context.getBean(DbUtil.class);

		long ts = dbUtil.readAcqDataMaxTimestamp();
		Map<String,SystemVariable> vars = dbUtil.readSystemVar("%", ts);
		int maxChannel = Integer.parseInt(vars.get("acq_n_channel").getValue(0));
		
		List<AcqDataEntry> data = dbUtil.readAcqData(ts, ts);
		
		//XStream stream = new XStream();
		//System.out.println(stream.toXML(data));
		
		int lastSampleInd = 0;
		for (AcqDataEntry ent : data) {
			int newSampleInd = ent.getSampleInd();
			assertTrue(newSampleInd >= lastSampleInd);
			newSampleInd = lastSampleInd;
			
			int channel = ent.getChannel(); 
			assertTrue(channel < maxChannel);
			
			double val = ent.getValue();
			
			String channelType = vars.get("acq_channel_type").getValue(channel);
			if (channelType.equalsIgnoreCase("analog")) {
				assertTrue (val <= Double.parseDouble(vars.get("acq_channel_max_value").getValue(channel))
						&& val >= Double.parseDouble(vars.get("acq_channel_min_value").getValue(channel)));
			} else if (channelType.equalsIgnoreCase("half_digital")) {
				assertTrue ((int)val == DigitalChannel.UP 
						||(int)val == DigitalChannel.DOWN);
			}
		}
	}
}
