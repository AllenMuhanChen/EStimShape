function [sig,np,spks]= sbxpullsignals(fname)

load([fname '.segment'],'-mat'); % load segmentation

if(~exist('np_mask','var'))
    
    np = [];
    
    z = sbxread(fname,1,1);
    
    global info;
    
    ncell = max(mask(:));
    
    for(i=1:ncell)
        idx{i} = find(mask==i);
    end
    
    sig = zeros(info.max_idx+1, ncell);
    
    h = waitbar(0,sprintf('Pulling %d signals out...',ncell));
    
    for(i=0:info.max_idx)
        waitbar(i/(info.max_idx-1),h);          % update waitbar...
        z = sbxread(fname,i,1);
        z = squeeze(z(1,:,:));
        %    z = circshift(z,info.aligned.T(i+1,:)); % align the image
        for(j=1:ncell)                          % for each cell
            sig(i+1,j) = mean(z(idx{j}));       % pull the mean signal out...
        end
    end
    
    
    
    delete(h);
    
    save([fname '.signals'],'sig');     % append the motion estimate data...
    
else
    
    z = sbxread(fname,1,1);
    
    global info;
    
    ncell = max(mask(:));
    
    for(i=1:ncell)
        idx{i} = find(mask==i);
        np_idx{i} = find(np_mask{i}>0);
    end
    
    sig = zeros(info.max_idx+1, ncell);
    np = zeros(size(sig));
    spks = zeros(size(sig));

    h = waitbar(0,sprintf('Pulling %d signals/neuropil out...',ncell));
    
    for(i=0:info.max_idx)
        waitbar(i/(info.max_idx-1),h);          % update waitbar...
        z = sbxread(fname,i,1);
        z = squeeze(z(1,:,:));
        %    z = circshift(z,info.aligned.T(i+1,:)); % align the image
        for(j=1:ncell)                          % for each cell
            sig(i+1,j) = mean(z(idx{j}));       % pull the mean signal out...
            np(i+1,j) = median(z(np_idx{j}));
        end
    end
    
    for i = 1:ncell
        % spks(:,i) = deconv(sig(:,i), [0.33    1.8503    0.2958    9.3894]);
         spks(:,i) = deconv(sig(:,i), [1.5    1.8503    0.2958    9.3894]);
    end
                 
    
    delete(h);
     
    save([fname '.signals'],'sig','np','spks');     % append the motion estimate data...
 
end



function y = deconv(y,x)

s = x(1);   % sigma
th = x(2);  % theta
b = x(3);   % beta
a = x(4);   % alpha

nsamp = size(y,1);

% Odd filter

t = 0:nsamp-1;
w = t.*exp(-t.^2 / (2*s^2));
w(2:end) = (w(2:end)-w(end:-1:2));
w = -w';
w = w/norm(w);

% Even filter

w0 = zeros(nsamp,1);
w0 = exp(-t.^2 / (2*s^2));
w0(2:end) = (w0(2:end)+w0(end:-1:2));
w0 = w0';
w0 = w0/norm(w0);
 
% Filtered signals

wf0 = fft(w0);
xf0 = real(ifft(fft(y(1:nsamp)).*wf0));
xf0 = zscore(xf0);

wf = fft(w);
xf = real(ifft(fft(y(1:nsamp)).*wf));
xf = zscore(xf);

% Of course one can combine the filters first and convolve once...
% but for historical reasons I kept them separate.

% Linear combination of filtered signals

xf = cosd(a)*xf+sind(a)*xf0;

% Output nonlinearity

y(1:nsamp) = (xf-th).^b .* (xf>=th);



