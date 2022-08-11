function [trial_data] = SaveTrialData(tstamp1, tstamp2, filepath)
% filepath = "/Users/allenchen/Documents/SimpleUnimodalTestData";
trial_data = GetTrialData(tstamp1, tstamp2);
save(filepath, 'trial_data');
end

