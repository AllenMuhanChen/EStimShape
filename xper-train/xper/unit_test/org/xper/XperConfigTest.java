package org.xper;

import java.io.UnsupportedEncodingException;
import java.net.URL;

import junit.framework.TestCase;

import org.apache.log4j.Logger;
import org.junit.Test;
import org.xper.util.FileUtil;

import static org.junit.Assert.assertTrue;

public class XperConfigTest {
	static Logger logger = Logger.getLogger(XperConfigTest.class);
	
	String getCodeSourceDir(Class<?> claz) {
		URL url = FileUtil.getCodeSourceUrl(claz);
		logger.info (FileUtil.fileUrlToPath(url));
		return FileUtil.fileUrlToPath(url);
	}

	@Test
	public void testCodeSourceDir () {
		assertTrue(getCodeSourceDir(this.getClass()).endsWith("class"));	
	}

	@Test
	public void testCodeSourceDirJarFile() {
		assertTrue(getCodeSourceDir(org.lwjgl.opengl.GL11.class).endsWith("lwjgl.jar"));
	}

	@Test
	public void testFileDir () throws UnsupportedEncodingException {
		URL url = FileUtil.getUrlForObject(this.getClass());
		logger.info(FileUtil.fileUrlToPath(url));
		assertTrue(FileUtil.fileUrlToPath(url).endsWith("ConfigTest.class"));
	}
}
