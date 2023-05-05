package org.xper.util;

import java.io.File;

import jdk.nashorn.internal.ir.annotations.Ignore;
import junit.framework.TestCase;

@Ignore
public class FileUtilTest extends TestCase {
	public void testListDirectories () {
		FileUtil.walkDirectories(new File("/home/wang/workspace/xper-src/dist/"), 
			new FileUtil.FileVisitor() {
				public boolean visitDirectory(File f) {
					System.out.println(f.getAbsolutePath());
					return true;
				}
				public void visitFile(File f) {
				}});
	}
}
