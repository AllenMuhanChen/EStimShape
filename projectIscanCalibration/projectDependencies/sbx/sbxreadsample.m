function z = sbxreadsample(fname,N,pmt)

% read a random set of N images in the stack of pmt (1-green, 2-red)

global info;

z = sbxread(fname,1,1);
z = zeros([size(z,2) size(z,3) N]);
idx = floor(rand(1,N)*info.max_idx);

%h = waitbar(0,sprintf('Reading %d sample frames',N));
for(j=1:length(idx))
%    waitbar(j/length(idx),h);
    q = sbxread(fname,idx(j),1);
    z(:,:,j) = squeeze(q(pmt,:,:));
end
%delete(h);
