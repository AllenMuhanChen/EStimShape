
package org.xper.allen.experiment;
import org.xper.allen.specs.EStimSpec;

public class EStimSpecGenerator {
	int chan = 1;
	String trig_src = "";
	int num_pulses = 1;
	float pulse_train_period = 0;
	float post_stim_refractory_period = 0;
	String stim_shape = "Biphasic";
	String stim_polarity = "Cathodic";
	float d1 = 100;
	float d2 = 100;
	float dp = 0;
	float a1 = 100;
	float a2 = 100;
	float pre_stim_amp_settle = 0;
	float post_stim_amp_settle = 0;
	int maintain_amp_settle_during_pulse_train = 0;
	float post_stim_charge_recovery_on = 0;
	float post_stim_charge_recovery_off = 0;
	
	public EStimSpec generate () {
		EStimSpec e = new EStimSpec();
		e.set_chan(chan);
		e.set_trig_src(trig_src);
		e.set_num_pulses(num_pulses);
		e.set_pulse_train_period(pulse_train_period);
		e.set_post_stim_refractory_period(post_stim_refractory_period);
		e.set_stim_shape(stim_shape);
		e.set_stim_polarity(stim_polarity);
		e.set_d1(d1);
		e.set_d2(d2);
		e.set_dp(dp);
		e.set_a1(a1);
		e.set_a2(a2);
		e.set_pre_stim_amp_settle(pre_stim_amp_settle);
		e.set_post_stim_amp_settle(post_stim_amp_settle);
		e.set_maintain_amp_settle_during_pulse_train(maintain_amp_settle_during_pulse_train);
		e.set_post_stim_charge_recovery_on(post_stim_charge_recovery_on);
		e.set_post_stim_charge_recovery_off(post_stim_charge_recovery_off);
		return e;
	}

	public EStimSpec generateStimSpec() {
		return this.generate();
	}

	public int getChan() {
		return chan;
	}

	public void setChan(int chan) {
		this.chan = chan;
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
}