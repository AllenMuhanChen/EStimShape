package org.xper.sach.util;

import java.text.SimpleDateFormat;
import java.util.Date;

public class DateTimeUtil {

	public static final String FORMAT_PATTERN = "yyyyMMddHHmmss.SSS000";

	public static Date parse(String ds) throws Throwable {

		String[] tokens = ds.split("\\.");
		if (tokens.length != 2) {
			throw new Exception("Invalid date string: " + ds);
		}
		int fractionalSecs = Integer.parseInt(tokens[1]) / 1000;
		return new SimpleDateFormat("yyyyMMddHHmmss.SSS").parse(String.format("%s.%03d", tokens[0], fractionalSecs));
	}

	public static String format(Date date) {

		return new SimpleDateFormat(FORMAT_PATTERN).format(date);
	}

}