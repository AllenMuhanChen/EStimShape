package org.xper.util;

import java.text.SimpleDateFormat;
import java.util.Calendar;

public class DateUtil {
	static SimpleDateFormat timestampDateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
	public static String timestampToDateString(long ts) {
		Calendar cal = Calendar.getInstance();
		cal.setTimeInMillis(ts / 1000);
		return timestampDateFormat.format(cal.getTime());
	}
}
