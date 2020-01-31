//AC
package org.xper.allen.specs;


public class BlockSpec {
	long id;
	int num_stims_only;
	int num_estims_only;
	int num_catches;
	int num_both;
	String shuffle;
	
	public long get_id() {
		return id;
	}
	public void set_id(long id) {
		this.id = id;
	}
	public int get_num_stims_only() {
		return num_stims_only;
	}
	public void set_num_stims_only(int num_stims_only) {
		this.num_stims_only = num_stims_only;
	}
	public int get_num_estims_only() {
		return num_estims_only;
	}
	public void set_num_estims_only(int num_estims_only) {
		this.num_estims_only = num_estims_only;
	}
	public int get_num_catches() {
		return num_catches;
	}
	public void set_num_catches(int num_catches) {
		this.num_catches = num_catches;
	}
	public int get_num_both() {
		return num_both;
	}
	public void set_num_both(int num_both) {
		this.num_both = num_both;
	}
	public String get_shuffle() {
		return shuffle;
	}
	public void set_shuffle(String shuffle) {
		this.shuffle = shuffle;
	}
}
