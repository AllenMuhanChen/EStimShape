function [r,stat] = sbxhartley(fname)

% analyze sparse noise experiment

% edit Luis 1/10/17. Allow rigid and nonrigid .signals files as input..
    % -----
    if contains(fname,'rigid') % search for rigid in filename
        si = strfind(fname,'_'); 
        fnamelog = fname( 1:si(end)-1); % remove it
    else 
        fnamelog = fname;
    end
    % -----

%%
log = sbxreadhartleylog(fnamelog); % read log
log = log{1};       % assumes only 1 trial
max_k = max(abs(log.kx));

load([fname, '.signals'],'-mat');    % load signals

% Dario - now signals are deconvolved in the segmentation tool
% sig = medfilt1(sig,11);             % median filter
% sig = zscore(sig);
% dsig = diff(sig);    
% p = prctile(dsig,65);
% dsig = bsxfun(@minus,dsig,p);
% dsig = dsig .* (dsig>0);
% dsig = zscore(dsig);

dsig = spks;

ncell = size(dsig,2);
nstim = size(log,1);

ntau = 20;

r = zeros(2*max_k+1,2*max_k+1,ntau,ncell);

h = waitbar(0,'Processing...');
for(i=1:nstim)
        r(log.kx(i)+1+max_k,log.ky(i)+1+max_k,:,:) =  squeeze(r(log.kx(i)+1+max_k,log.ky(i)+1+max_k,:,:)) + ...
            dsig(log.sbxframe(i)-2:log.sbxframe(i)+ntau-3,:);
    waitbar(i/nstim,h);
end
delete(h);

h = fspecial('gauss',5,1);
hh = waitbar(0,'Filtering...');
k = 0;
for(t=1:ntau)
    for(n = 1:ncell)
        rf = squeeze(r(:,:,t,n));
        rf = rf + rot90(rf,2); % symmetry 
        r(:,:,t,n) = filter2(h,rf,'same');
        k = k+1;
        waitbar(k/(13*2*ncell),hh);
    end
end
delete(hh);

hh = waitbar(0,'Statistics...');

[xx,yy] = meshgrid(-12:12,-12:12);
zz = xx+1i*yy;
zz = abs(zz).*exp(1i*angle(zz)*2);

for i = 1:size(r,4)
    z = squeeze(r(:,:,:,i));
    q = reshape(z,25^2,[]);
    k = kurtosis(q)-3;
    [kmax,t] = max(k);
    tmax = t-3;    
    stat(i).k = k;
    stat(i).tmax = tmax;
    stat(i).kmax = kmax;
    stat(i).kern = squeeze(z(:,:,t));
    stat(i).sig = (kmax>7);
    
    % estimate ori/sf
    bw = stat(i).kern>(max(stat(i).kern(:))*.95);
    idx = find(bw);
    zzm = mean(zz(idx));
    zzm = abs(zzm)*exp(1i*angle(zzm)/2);
    
    stat(i).sf = abs(zzm);
    stat(i).ori = angle(zzm);
    
    if(stat(i).sig)
        clf
        imagesc(-12:12,-12:12,stat(i).kern);
        hold on;
        plot([0 real(zzm)],[0 imag(zzm)],'wo-','linewidth',3,'markersize',14);
%         pause(1);
    end
end

delete(hh);

save([fname '.hartley'],'r','stat','-v7.3');


