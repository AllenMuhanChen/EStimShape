function [spikes,a] = sbxesd(sig,order,th)

% Extremely simple deconvolution (dlr, 9/27/16)

% sig is the signal obtained after extraction (nframes[rows] x
% ncells[cols]) using, for example, sbxpullsignals()
% order is the order of the linear predictive coding (order = 8 works well
% for GCamp6f)
% th is the threshold for spike detection.  Usually th in the range 2.0 to 2.3 works Ok for
% Gcamp6.  Start with th = 2.15.

% spikes - is the output and contains the spikes (the size is the same as
% the size of sig, locations where the values are 1 indicate a detected
% spike).

% LPC coefficient calculation

[a,~] = lpc(sig,order);

% compute residuals 

y = zeros(size(sig));
for(i=1:size(sig,2))
    y(:,i) = sig(:,i) - filter([0 -a(i,2:end)],1,sig(:,i));
end

% thresholding for spike detection 

M = median(y);
s = 1.4826*(mad(y,1));
spikes = bsxfun(@gt,y,M+th*s);
