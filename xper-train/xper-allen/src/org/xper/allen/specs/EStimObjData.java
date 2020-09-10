//AC
package org.xper.allen.specs;

import java.util.ArrayList;

public class EStimObjData {
	long id;
	String chans;
	float post_trigger_delay;
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
	public long getId() {
		return id;
	}
	public void setId(long id) {
		this.id = id;
	}
	public String getChans() {
		return chans;
	}
	public void setChans(String chans) {
		this.chans = chans;
	}
	public float getPost_trigger_delay() {
		return post_trigger_delay;
	}
	public void setPost_trigger_delay(float post_trigger_delay) {
		this.post_trigger_delay = post_trigger_delay;
	}
	public String getTrig_src() {
		return trig_src;
	}
	public void setTrig_src(String trig_src) {
		this.trig_src = trig_src;
	}
	public int getNum_pulses() {
		return num_pulses;
	}
	public void setNum_pulses(int num_pulses) {
		this.num_pulses = num_pulses;
	}
	public float getPulse_train_period() {
		return pulse_train_period;
	}
	public void setPulse_train_period(float pulse_train_period) {
		this.pulse_train_period = pulse_train_period;
	}
	public float getPost_stim_refractory_period() {
		return post_stim_refractory_period;
	}
	public void setPost_stim_refractory_period(float post_stim_refractory_period) {
		this.post_stim_refractory_period = post_stim_refractory_period;
	}
	public String getStim_shape() {
		return stim_shape;
	}
	public void setStim_shape(String stim_shape) {
		this.stim_shape = stim_shape;
	}
	public String getStim_polarity() {
		return stim_polarity;
	}
	public void setStim_polarity(String stim_polarity) {
		this.stim_polarity = stim_polarity;
	}
	public float getD1() {
		return d1;
	}
	public void setD1(float d1) {
		this.d1 = d1;
	}
	public float getD2() {
		return d2;
	}
	public void setD2(float d2) {
		this.d2 = d2;
	}
	public float getDp() {
		return dp;
	}
	public void setDp(float dp) {
		this.dp = dp;
	}
	public float getA1() {
		return a1;
	}
	public void setA1(float a1) {
		this.a1 = a1;
	}
	public float getA2() {
		return a2;
	}
	public void setA2(float a2) {
		this.a2 = a2;
	}
	public float getPre_stim_amp_settle() {
		return pre_stim_amp_settle;
	}
	public void setPre_stim_amp_settle(float pre_stim_amp_settle) {
		this.pre_stim_amp_settle = pre_stim_amp_settle;
	}
	public float getPost_stim_amp_settle() {
		return post_stim_amp_settle;
	}
	public void setPost_stim_amp_settle(float post_stim_amp_settle) {
		this.post_stim_amp_settle = post_stim_amp_settle;
	}
	public int getMaintain_amp_settle_during_pulse_train() {
		return maintain_amp_settle_during_pulse_train;
	}
	public void setMaintain_amp_settle_during_pulse_train(int maintain_amp_settle_during_pulse_train) {
		this.maintain_amp_settle_during_pulse_train = maintain_amp_settle_during_pulse_train;
	}
	public float getPost_stim_charge_recovery_on() {
		return post_stim_charge_recovery_on;
	}
	public void setPost_stim_charge_recovery_on(float post_stim_charge_recovery_on) {
		this.post_stim_charge_recovery_on = post_stim_charge_recovery_on;
	}
	public float getPost_stim_charge_recovery_off() {
		return post_stim_charge_recovery_off;
	}
	public void setPost_stim_charge_recovery_off(float post_stim_charge_recovery_off) {
		this.post_stim_charge_recovery_off = post_stim_charge_recovery_off;
	}
	
	/*
	public EStimObjData(EStimObjData d) {
		id = d.get_id();
		post_trigger_delay = d.get_post_trigger_delay();
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
	
	
}
