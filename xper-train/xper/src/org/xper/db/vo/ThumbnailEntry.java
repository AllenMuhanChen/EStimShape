package org.xper.db.vo;

public class ThumbnailEntry {
	/**
	 * It can be either the task id or the stim id. 
	 */
	long id;
	
	/**
	 * Binary format.
	 */
	byte [] thumbnail;

	public long getId() {
		return id;
	}

	public void setId(long id) {
		this.id = id;
	}

	public byte[] getThumbnail() {
		return thumbnail;
	}

	public void setThumbnail(byte[] thumbnail) {
		this.thumbnail = thumbnail;
	}
}
