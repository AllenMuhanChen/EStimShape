package org.xper.util;

import java.util.ResourceBundle;

public class ResourceManager {
	private static final String BUNDLE_NAME = "org.xper.resource.Resources";
	private static final ResourceBundle RESOURCE_BUNDLE = ResourceBundle
			.getBundle(BUNDLE_NAME);

	private ResourceManager() {
	}

	/**
	 * Get string value from Resources.properties file.
	 * 
	 * @param key
	 * @return string value for the key.
	 */
	public static String getString(String key) {
		return RESOURCE_BUNDLE.getString(key);
	}
}
