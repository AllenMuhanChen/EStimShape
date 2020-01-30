package org.xper;

import java.io.File;
import java.lang.reflect.Field;
import java.util.List;

import org.apache.log4j.Logger;
import org.xper.util.FileUtil;

public class XperConfig {
	static {
		System.setProperty("java.net.preferIPv4Stack", "true");
	}
	
	static Logger logger = Logger.getLogger(XperConfig.class);

	public XperConfig(String nativeLibraryPath, List<String> libs) {
		configNativeLibrary(nativeLibraryPath, libs);
	}

	private void configNativeLibrary(String nativeLibraryPath, List<String> libs) {
		StringBuffer strLibPathBuffer = new StringBuffer();
		strLibPathBuffer.append(System.getProperty("java.library.path"));
		
		strLibPathBuffer.append(File.pathSeparator
				+ getNativeLibPath().replace(';', File.pathSeparatorChar).replace('/', File.separatorChar));
		
		strLibPathBuffer.append(File.pathSeparator
				+ nativeLibraryPath.replace(';', File.pathSeparatorChar).replace('/', File.separatorChar));
		System.setProperty("java.library.path", strLibPathBuffer.toString());

		if (logger.isDebugEnabled()) {
			String path = System.getProperty("java.library.path");
			logger.debug(path.replace(File.pathSeparator, System.getProperty("line.separator")));
		}

		Class<?> loaderClass = ClassLoader.class;
		Field userPaths;
		try {
			userPaths = loaderClass.getDeclaredField("sys_paths");
			userPaths.setAccessible(true);
			userPaths.set(null, null);
		} catch (Exception e) {
			e.printStackTrace();
		}
		
		for (String lib : libs) {
			System.loadLibrary(lib);
		}
	}
	
	String getNativeLibPath () {
		final StringBuffer buf = new StringBuffer();
		String basePath = FileUtil.fileUrlToPath(FileUtil.getCodeSourceUrl(this.getClass()));
		if (logger.isDebugEnabled()) {
			logger.debug("Native library base path: " + basePath);
		}
		FileUtil.FileVisitor visitor = new FileUtil.FileVisitor(){
			public boolean visitDirectory(File f) {
				String name = f.getName();
				if (!name.startsWith(".")) {
					buf.append(f.getAbsolutePath()+";");
					return true;
				} else {
					return false;
				}
			}
			public void visitFile(File f) {
			}
		};
		if (FileUtil.isFile(basePath)) {
			String xperPath = FileUtil.getParent(basePath);
			// xper.jar in dist folder		
			FileUtil.walkDirectories(new File(xperPath), visitor);
		} else {
			// class folder
			String xperPath = FileUtil.getParent(basePath);
			FileUtil.walkDirectories(new File(xperPath + "/lib"), visitor);
			
			String xperNativePath = FileUtil.getParent(xperPath) + "/xper-native";
			FileUtil.walkDirectories(new File(xperNativePath), visitor);
		}
		return buf.toString();
	}
}
