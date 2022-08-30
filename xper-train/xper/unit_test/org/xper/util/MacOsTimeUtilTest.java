package org.xper.util;

import java.util.ArrayList;
import java.util.List;

import org.xper.XperConfig;
import org.xper.time.DefaultTimeUtil;

import junit.framework.TestCase;

public class MacOsTimeUtilTest extends TestCase {
	public void test () {
		List<String> libs = new ArrayList<String>();
		libs.add("xper");
		new XperConfig("", libs);
		
		for (int i = 0; i < 10; i ++) {
			DefaultTimeUtil util = new DefaultTimeUtil();
			long t1 = util.currentTimeMicros();
			//long t2 = System.currentTimeMillis()*1000;
			//long diff = t2 - t1;
			//System.out.println(diff);
			//assertEquals(0, diff, 1000);
			ThreadUtil.sleep(1000);
			long t2 = util.currentTimeMicros();
			System.out.println(t2 - t1);
		}
	}
}
