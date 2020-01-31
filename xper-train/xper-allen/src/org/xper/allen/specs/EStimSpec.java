//AC
package org.xper.allen.specs;

public class EStimSpec {
	//long id;
	int chan;
	String trig_src;
	int num_pulses;
	float pulse_train_period;
	float post_stim_refractory_period;
	String stim_shape;
	String stim_polarity;
	float d1;
	float d2;
	float dp;
	float a1;
	float a2;
	float pre_stim_amp_settle;
	float post_stim_amp_settle;
	int maintain_amp_settle_during_pulse_train;
	float post_stim_charge_recovery_on;
	float post_stim_charge_recovery_off;
	
	/*
	public EStimSpec(EStimSpec d) {
		id = d.get_id();
		chan = d.get_chan();
		trig_src = d.get_trig_src();
		num_pulses = d.get_num_pulses();
		pulse_train_period = d.get_pulse_train_period();
		post_stim_refractory_period = d.get_post_stim_refractory_period();
		stim_shape = d.get_stim_shape();
		stim_polarity = d.get_stim_polarity();
		d1 = d.get_d1();
		d2 = d.get_d2();
		dp = d.get_dp();
		a1 = d.get_a1();
		a2 = d.get_a2();
		pre_stim_amp_settle = d.get_pre_stim_amp_settle();
		post_stim_amp_settle = d.get_post_stim_amp_settle();
		maintain_amp_settle_during_pulse_train = d.get_maintain_amp_settle_during_pulse_train();
		post_stim_charge_recovery_on = d.get_post_stim_charge_recovery_on();
		post_stim_charge_recovery_off = d.get_post_stim_charge_recovery_off();
	}
	*/
	/*
	public long get_id() {
		return id;
	}
	public void set_id(long id_) {
		id = id_;
	}
	*/
	public int get_chan() {
		return chan;
	}
	public void set_chan(int chan_) {
		chan = chan_;
	}
	public String get_trig_src() {
		return trig_src;
	}
	public void set_trig_src(String trig_src_) {
		trig_src = trig_src_;
	}
	public int get_num_pulses() {
		return num_pulses;
	}
	public void set_num_pulses(int num_pulses_) {
		num_pulses = num_pulses_;
	}
	public float get_pulse_train_period() {
		return pulse_train_period;
	}
	public void set_pulse_train_period(float pulse_train_period_) {
		pulse_train_period = pulse_train_period_;
	}	
	public float get_post_stim_refractory_period() {
		return post_stim_refractory_period;
	}
	public void set_post_stim_refractory_period(float post_stim_refractory_period_) {
		post_stim_refractory_period = post_stim_refractory_period_;
	}
	public String get_stim_shape() {
		return stim_shape;
	}
	public void set_stim_shape(String stim_shape_) {
		stim_shape = stim_shape_;
	}
	public String get_stim_polarity() {
		return stim_polarity;
	}
	public void set_stim_polarity(String stim_polarity_) {
		stim_polarity = stim_polarity_;
	}
	public float get_d1() {
		return d1;
	}
	public void set_d1(float d1_) {
		d1 = d1_;
	}
	public float get_d2() {
		return d2;
	}
	public void set_d2(float d2_) {
		d2 = d2_;
	}
	public float get_dp() {
		return dp;
	}
	public void set_dp(float dp_) {
		dp = dp_;
	}
	public float get_a1() {
		return a1;
	}
	public void set_a1(float a1_) {
		a1 = a1_;
	}
	public float get_a2() {
		return a2;
	}
	public void set_a2(float a2_) {
		a2 = a2_;
	}
	public float get_pre_stim_amp_settle() {
		return pre_stim_amp_settle;
	}
	public void set_pre_stim_amp_settle(float pre_stim_amp_settle_) {
		pre_stim_amp_settle = pre_stim_amp_settle_;
	}
	public float get_post_stim_amp_settle() {
		return post_stim_amp_settle;
	}
	public void set_post_stim_amp_settle(float post_stim_amp_settle_) {
		post_stim_amp_settle = post_stim_amp_settle_;
	}
	public int get_maintain_amp_settle_during_pulse_train() {
		return maintain_amp_settle_during_pulse_train;
	}
	public void set_maintain_amp_settle_during_pulse_train(int maintain_amp_settle_during_pulse_train_) {
		maintain_amp_settle_during_pulse_train = maintain_amp_settle_during_pulse_train_;
	}
	public float get_post_stim_charge_recovery_on() {
		return post_stim_charge_recovery_on;
	}
	public void set_post_stim_charge_recovery_on(float post_stim_charge_recovery_on_) {
		post_stim_charge_recovery_on = post_stim_charge_recovery_on_;
	}
	public float get_post_stim_charge_recovery_off() {
		return post_stim_charge_recovery_off;
	}
	public void set_post_stim_charge_recovery_off(float post_stim_charge_recovery_off_) {
		post_stim_charge_recovery_off = post_stim_charge_recovery_off_;
	}
}
