package org.xper;

import java.io.UnsupportedEncodingException;
import java.net.URL;

import junit.framework.TestCase;

import org.apache.log4j.Logger;
import org.xper.util.FileUtil;

public class XperConfigTest extends TestCase {
	static Logger logger = Logger.getLogger(XperConfigTest.class);
	
	String getCodeSourceDir(Class<?> claz) {
		URL url = FileUtil.getCodeSourceUrl(claz);
		logger.info (FileUtil.fileUrlToPath(url));
		return FileUtil.fileUrlToPath(url);
	}
	
	public void testCodeSourceDir () {
		assertTrue(getCodeSourceDir(this.getClass()).endsWith("class"));	
	}
	
	public void testCodeSourceDirJarFile() {
		assertTrue(getCodeSourceDir(org.lwjgl.opengl.GL11.class).endsWith("lwjgl.jar"));
	}
	
	public void testFileDir () throws UnsupportedEncodingException {
		URL url = FileUtil.getUrlForObject(this.getClass());
		logger.info(FileUtil.fileUrlToPath(url));
		assertTrue(FileUtil.fileUrlToPath(url).endsWith("ConfigTest.class"));
	}
}
