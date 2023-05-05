function z = sbxreadskip(fname,N,skip,varargin)

% read a set of N images skip frames apart and correct for rigid motion

global info;

z = sbxread(fname,1,1);
z = zeros([size(z,2) size(z,3) N]);
idx = (0:N-1)*skip;

h = waitbar(0,sprintf('Reading %d frames',N));
for(j=1:length(idx))
    waitbar(j/length(idx),h);
    q = sbxread(fname,idx(j),1);
    %z(:,:,j) = circshift(squeeze(q(1,:,:)),info.aligned.T(idx(j)+1,:));
    z(:,:,j) = squeeze(q(1,:,:));
end
delete(h);
