package org.xper.util;

import java.io.File;
import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;
import java.net.URLDecoder;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import org.xper.XperConfig;
import org.xper.exception.ExperimentSetupException;
import org.xper.exception.FileURLFormatException;
import org.xper.exception.RuntimeIOException;

public class FileUtil {	
	static {
		loadSystemProperties();
		configClassPath();
	}
	
	public interface FileVisitor {
		public void visitFile (File f);
		/**
		 * Continue walking if return true.
		 */
		public boolean visitDirectory (File f);
	}
	
	public static void addJarFilesToClassPath(List<File> fileList) {
	      URLClassLoader sysloader = (URLClassLoader) ClassLoader.getSystemClassLoader();
	      Class<?> sysclass = URLClassLoader.class;
	      final Class<?>[] parameters = new Class<?>[]{URL.class};
	      try {
	         Method method = sysclass.getDeclaredMethod("addURL", parameters);
	         method.setAccessible(true);
	         for (File f : fileList) {
	        	 method.invoke(sysloader, new Object[]{f.toURI().toURL()});
	         }
	      } catch (Throwable t) {
	         throw new RuntimeIOException("Error, could not add URL to system classloader");
	      }
	   }
	
	public static List<File> getDistJarFileList(String xperDistPath) {
		final ArrayList<File> result = new ArrayList<File>();
		FileUtil.FileVisitor visitor = new FileUtil.FileVisitor(){
			public boolean visitDirectory(File f) {
				String name = f.getName();
				if (!name.startsWith(".")) {					
					return true;
				} else {
					return false;
				}
			}
			public void visitFile(File f) {
				String name = f.getName();
				if (name.endsWith(".jar")) {
					result.add(f);
				}
			}
		};
		FileUtil.walkDirectories(new File(xperDistPath), visitor);
		return result;
	}
	
	public static void configClassPath() {
		String basePath = FileUtil.fileUrlToPath(FileUtil.getCodeSourceUrl(XperConfig.class));
		if (FileUtil.isFile(basePath)) {
			String xperPath = FileUtil.getParent(basePath);
			// xper.jar in dist folder
			List<File> jarFileList = getDistJarFileList(xperPath);
			addJarFilesToClassPath(jarFileList);
		}
	}
	
	public static void walkDirectories(File base, FileVisitor visitor) {
		if (base.isDirectory()) {
			if (visitor.visitDirectory(base)) {		
				File [] all = base.listFiles();
				for (File f : all) {
					walkDirectories(f, visitor);
				}
			}
		} else {
			visitor.visitFile(base);
		}
	}
	
	public static Class<?> loadConfigClass (String propName) {
		return loadConfigClass(propName, null);
	}
	
	public static Class<?> loadConfigClass (String propName, Class<?> defaultClass) {
		String className = System.getProperty(propName);
		if (className == null || className.trim().length() == 0) {
			if (defaultClass == null) {
				throw new ExperimentSetupException("Please provide the config class name in xper.properties.");
			} else {
				return defaultClass;
			}
		} else {
			try {
				return Class.forName(className);
			} catch (ClassNotFoundException e) {
				throw new ExperimentSetupException("Cannot not load config class " + className + " set in property " + propName, e);
			}
		}
	}
	
	public static void loadSystemProperties () {
		Properties props = new Properties(System.getProperties());
		try {
			props.load(XperConfig.class.getResourceAsStream("/xper.properties"));
		} catch (IOException e) {
			throw new ExperimentSetupException("Cannot find xper.properties file.", e);
		}
		System.setProperties(props);
	}
	
	public static boolean isFile (String path) {
		File f = new File(path);
		return f.isFile();
	}
	
	public static String getParent (String path) {
		File f = new File(path);
		return f.getParent();
	}
	
	public static URL getUrlForObject (Class<?> claz) {
		String name = claz.getName();
		int index = name.lastIndexOf('.');
		name = name.substring(index + 1) + ".class";
		return claz.getResource(name);
	}
	
	public static String fileUrlToPath (URL url) {
		String proto = url.getProtocol();
		if (proto.equals("file")) {
			try {
				File file = new File (URLDecoder.decode(url.getPath(), "UTF-8"));
				return file.getPath();
			} catch (UnsupportedEncodingException e) {
				throw new FileURLFormatException(e);
			}
		} else {
			throw new FileURLFormatException("Incorrect protocol: " + proto);
		}
	}
	
	public static URL getCodeSourceUrl (Class<?> claz) {
		URL path = claz.getProtectionDomain().getCodeSource().getLocation();
		return path;
	}
}
